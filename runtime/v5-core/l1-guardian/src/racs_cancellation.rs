use std::collections::HashSet;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::sync::Mutex;

use base64::{engine::general_purpose::{STANDARD, URL_SAFE_NO_PAD}, Engine};
use chrono::{DateTime, Utc};
use ed25519_dalek::{Signature, Verifier};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};

use super::racs_permit::{SignedArtifact, TrustedPermitIssuer};

const SCHEMA_VERSION: &str = "0.2.0";
const CANONICALIZATION: &str = "RACS-JCS-1";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CancellationAuthorizationPayload {
    pub cancellation_authorization_id: String,
    pub cancellation_request_id: String,
    pub tenant_id: String,
    pub task_id: String,
    pub execution_id: String,
    pub execution_permit_id: String,
    pub execution_permit_digest: String,
    pub commit_token_id: String,
    pub commit_token_digest: String,
    pub source_revocation_event_id: String,
    pub decision: String,
    pub effective_at: String,
    pub valid_until: String,
    pub evidence_refs: Vec<String>,
    pub idempotency_key: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct InvalidationRecord {
    pub cancellation_authorization_id: String,
    pub tenant_id: String,
    pub task_id: String,
    pub execution_id: String,
    pub execution_permit_id: String,
    pub commit_token_id: String,
    pub source_revocation_event_id: String,
    pub invalidated_at: String,
    pub reason: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CancellationError {
    InvalidJson,
    WrongArtifactType,
    UnsupportedSchema,
    UnsupportedCanonicalization,
    WrongIssuer,
    WrongIssuerRole,
    WrongKey,
    WrongTenant,
    WrongTrustDomain,
    InactiveKey,
    InvalidTime,
    NotYetEffective,
    Expired,
    PayloadDigestMismatch,
    InvalidSignature,
    InvalidPayload,
    MissingBinding(&'static str),
    WrongDecision,
    DuplicateAuthorization,
    RegistryUnavailable,
}

pub struct CancellationVerifier {
    trusted: TrustedPermitIssuer,
}

impl CancellationVerifier {
    pub fn new(trusted: TrustedPermitIssuer) -> Self {
        Self { trusted }
    }

    pub fn verify_json(
        &self,
        encoded: &str,
        now: DateTime<Utc>,
    ) -> Result<(SignedArtifact, CancellationAuthorizationPayload), CancellationError> {
        let artifact: SignedArtifact = serde_json::from_str(encoded).map_err(|_| CancellationError::InvalidJson)?;
        self.verify(&artifact, now)?;
        let payload: CancellationAuthorizationPayload = serde_json::from_value(artifact.payload.clone())
            .map_err(|_| CancellationError::InvalidPayload)?;
        self.validate_payload(&artifact, &payload, now)?;
        Ok((artifact, payload))
    }

    fn verify(&self, artifact: &SignedArtifact, now: DateTime<Utc>) -> Result<(), CancellationError> {
        if artifact.artifact_type != "CANCELLATION_AUTHORIZATION" {
            return Err(CancellationError::WrongArtifactType);
        }
        if artifact.schema_version != SCHEMA_VERSION {
            return Err(CancellationError::UnsupportedSchema);
        }
        if artifact.canonicalization != CANONICALIZATION {
            return Err(CancellationError::UnsupportedCanonicalization);
        }
        if artifact.issuer_id != self.trusted.issuer_id {
            return Err(CancellationError::WrongIssuer);
        }
        if artifact.issuer_role != self.trusted.issuer_role || artifact.issuer_role != "REHT_CANCELLATION_AUTHORITY" {
            return Err(CancellationError::WrongIssuerRole);
        }
        if artifact.signature.algorithm != "Ed25519" || artifact.signature.key_id != self.trusted.key_id {
            return Err(CancellationError::WrongKey);
        }
        if artifact.tenant_id != self.trusted.tenant_id {
            return Err(CancellationError::WrongTenant);
        }
        if artifact.trust_domain != self.trusted.trust_domain {
            return Err(CancellationError::WrongTrustDomain);
        }
        if !self.trusted.active {
            return Err(CancellationError::InactiveKey);
        }

        let issued_at = parse_time(&artifact.issued_at)?;
        let expires_at = parse_time(&artifact.expires_at)?;
        if now < issued_at {
            return Err(CancellationError::NotYetEffective);
        }
        if now >= expires_at {
            return Err(CancellationError::Expired);
        }

        let canonical_payload = serde_jcs::to_vec(&artifact.payload).map_err(|_| CancellationError::InvalidPayload)?;
        if sha256_digest(&canonical_payload) != artifact.payload_digest {
            return Err(CancellationError::PayloadDigestMismatch);
        }

        let mut signature_input = artifact.clone();
        signature_input.signature.value.clear();
        let canonical_artifact = serde_jcs::to_vec(&signature_input).map_err(|_| CancellationError::InvalidJson)?;
        let signature_bytes = decode_signature(&artifact.signature.value)?;
        let signature = Signature::from_slice(&signature_bytes).map_err(|_| CancellationError::InvalidSignature)?;
        self.trusted
            .public_key
            .verify(&canonical_artifact, &signature)
            .map_err(|_| CancellationError::InvalidSignature)
    }

    fn validate_payload(
        &self,
        artifact: &SignedArtifact,
        payload: &CancellationAuthorizationPayload,
        now: DateTime<Utc>,
    ) -> Result<(), CancellationError> {
        if payload.tenant_id != artifact.tenant_id {
            return Err(CancellationError::WrongTenant);
        }
        for (name, value) in [
            ("cancellation_authorization_id", payload.cancellation_authorization_id.as_str()),
            ("cancellation_request_id", payload.cancellation_request_id.as_str()),
            ("task_id", payload.task_id.as_str()),
            ("execution_id", payload.execution_id.as_str()),
            ("execution_permit_id", payload.execution_permit_id.as_str()),
            ("commit_token_id", payload.commit_token_id.as_str()),
            ("source_revocation_event_id", payload.source_revocation_event_id.as_str()),
            ("idempotency_key", payload.idempotency_key.as_str()),
        ] {
            if value.is_empty() {
                return Err(CancellationError::MissingBinding(name));
            }
        }
        for (name, value) in [
            ("execution_permit_digest", payload.execution_permit_digest.as_str()),
            ("commit_token_digest", payload.commit_token_digest.as_str()),
        ] {
            if !is_digest(value) {
                return Err(CancellationError::MissingBinding(name));
            }
        }
        if payload.decision != "HALT" {
            return Err(CancellationError::WrongDecision);
        }
        if payload.evidence_refs.is_empty() || payload.idempotency_key.len() < 8 {
            return Err(CancellationError::InvalidPayload);
        }
        let effective_at = parse_time(&payload.effective_at)?;
        let valid_until = parse_time(&payload.valid_until)?;
        if now < effective_at {
            return Err(CancellationError::NotYetEffective);
        }
        if now >= valid_until {
            return Err(CancellationError::Expired);
        }
        if payload.cancellation_authorization_id != artifact.artifact_id {
            return Err(CancellationError::InvalidPayload);
        }
        Ok(())
    }
}

pub struct DurableInvalidationRegistry {
    path: PathBuf,
    authorization_ids: Mutex<HashSet<String>>,
    permit_ids: Mutex<HashSet<String>>,
    token_ids: Mutex<HashSet<String>>,
}

impl DurableInvalidationRegistry {
    pub fn open(path: impl AsRef<Path>) -> Result<Self, CancellationError> {
        let path = path.as_ref().to_path_buf();
        let mut authorization_ids = HashSet::new();
        let mut permit_ids = HashSet::new();
        let mut token_ids = HashSet::new();
        if path.exists() {
            let file = File::open(&path).map_err(|_| CancellationError::RegistryUnavailable)?;
            for line in BufReader::new(file).lines() {
                let line = line.map_err(|_| CancellationError::RegistryUnavailable)?;
                if line.trim().is_empty() {
                    continue;
                }
                let record: InvalidationRecord = serde_json::from_str(&line)
                    .map_err(|_| CancellationError::RegistryUnavailable)?;
                authorization_ids.insert(record.cancellation_authorization_id);
                permit_ids.insert(record.execution_permit_id);
                token_ids.insert(record.commit_token_id);
            }
        }
        Ok(Self {
            path,
            authorization_ids: Mutex::new(authorization_ids),
            permit_ids: Mutex::new(permit_ids),
            token_ids: Mutex::new(token_ids),
        })
    }

    pub fn invalidate(
        &self,
        artifact: &SignedArtifact,
        payload: &CancellationAuthorizationPayload,
        now: DateTime<Utc>,
    ) -> Result<InvalidationRecord, CancellationError> {
        let mut auth_ids = self.authorization_ids.lock().map_err(|_| CancellationError::RegistryUnavailable)?;
        let mut permit_ids = self.permit_ids.lock().map_err(|_| CancellationError::RegistryUnavailable)?;
        let mut token_ids = self.token_ids.lock().map_err(|_| CancellationError::RegistryUnavailable)?;
        if auth_ids.contains(&artifact.artifact_id) {
            return Err(CancellationError::DuplicateAuthorization);
        }
        let record = InvalidationRecord {
            cancellation_authorization_id: artifact.artifact_id.clone(),
            tenant_id: payload.tenant_id.clone(),
            task_id: payload.task_id.clone(),
            execution_id: payload.execution_id.clone(),
            execution_permit_id: payload.execution_permit_id.clone(),
            commit_token_id: payload.commit_token_id.clone(),
            source_revocation_event_id: payload.source_revocation_event_id.clone(),
            invalidated_at: timestamp(now),
            reason: "REHT_CANCELLATION_AUTHORIZATION".to_owned(),
        };
        let encoded = serde_json::to_vec(&record).map_err(|_| CancellationError::RegistryUnavailable)?;
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.path)
            .map_err(|_| CancellationError::RegistryUnavailable)?;
        file.write_all(&encoded).map_err(|_| CancellationError::RegistryUnavailable)?;
        file.write_all(b"\n").map_err(|_| CancellationError::RegistryUnavailable)?;
        file.sync_all().map_err(|_| CancellationError::RegistryUnavailable)?;
        auth_ids.insert(record.cancellation_authorization_id.clone());
        permit_ids.insert(record.execution_permit_id.clone());
        token_ids.insert(record.commit_token_id.clone());
        Ok(record)
    }

    pub fn is_permit_invalidated(&self, permit_id: &str) -> bool {
        self.permit_ids.lock().map(|ids| ids.contains(permit_id)).unwrap_or(true)
    }

    pub fn is_token_invalidated(&self, token_id: &str) -> bool {
        self.token_ids.lock().map(|ids| ids.contains(token_id)).unwrap_or(true)
    }
}

fn decode_signature(value: &str) -> Result<Vec<u8>, CancellationError> {
    URL_SAFE_NO_PAD
        .decode(value.as_bytes())
        .or_else(|_| STANDARD.decode(value.as_bytes()))
        .map_err(|_| CancellationError::InvalidSignature)
}

fn parse_time(value: &str) -> Result<DateTime<Utc>, CancellationError> {
    DateTime::parse_from_rfc3339(value)
        .map(|value| value.with_timezone(&Utc))
        .map_err(|_| CancellationError::InvalidTime)
}

fn timestamp(value: DateTime<Utc>) -> String {
    value.to_rfc3339_opts(chrono::SecondsFormat::AutoSi, true)
}

fn sha256_digest(data: &[u8]) -> String {
    format!("sha256:{:x}", Sha256::digest(data))
}

fn is_digest(value: &str) -> bool {
    value.len() == 71
        && value.starts_with("sha256:")
        && value[7..].chars().all(|character| character.is_ascii_hexdigit() && !character.is_ascii_uppercase())
}
