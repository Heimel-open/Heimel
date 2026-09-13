use std::collections::{HashMap, HashSet};
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
const PROFILE_ID: &str = "racs-core-0.2";
const CANONICALIZATION: &str = "RACS-JCS-1";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ContinuityEnforcementPayload {
    pub continuity_authorization_id: String,
    pub tenant_id: String,
    pub session_id: String,
    pub execution_id: String,
    pub execution_permit_id: String,
    pub execution_permit_digest: String,
    pub commit_token_id: String,
    pub commit_token_digest: String,
    pub continuity_decision_id: String,
    pub continuity_decision_digest: String,
    pub continuity_sequence: u64,
    pub decision: String,
    pub verification_decision: String,
    pub verification_reason_code: String,
    pub current_bounds_digest: String,
    pub effective_bounds_digest: String,
    pub narrowing_proof_digest: Option<String>,
    pub effective_at: String,
    pub valid_until: String,
    pub idempotency_key: String,
}

#[derive(Debug, Clone)]
pub struct ContinuityBindingContext {
    pub tenant_id: String,
    pub session_id: String,
    pub execution_id: String,
    pub execution_permit_id: String,
    pub execution_permit_digest: String,
    pub commit_token_id: String,
    pub commit_token_digest: String,
    pub initial_bounds_digest: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum ExecutionContinuityState {
    Active,
    BoundsModified,
    Paused,
    Stopped,
    Halted,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum CoreContinuityDirective {
    Continue,
    ApplyNarrowedBounds { effective_bounds_digest: String },
    Pause,
    Stop,
    Halt,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ContinuityEnforcementRecord {
    pub continuity_authorization_id: String,
    pub tenant_id: String,
    pub session_id: String,
    pub execution_id: String,
    pub execution_permit_id: String,
    pub commit_token_id: String,
    pub continuity_decision_id: String,
    pub continuity_sequence: u64,
    pub decision: String,
    pub previous_state: ExecutionContinuityState,
    pub next_state: ExecutionContinuityState,
    pub current_bounds_digest: String,
    pub effective_bounds_digest: String,
    pub verification_reason_code: String,
    pub enforced_at: String,
    pub idempotency_key: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ContinuityError {
    InvalidJson,
    WrongArtifactType,
    UnsupportedSchema,
    UnsupportedProfile,
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
    BindingMismatch(&'static str),
    VerificationRejected,
    InvalidVerificationReason,
    InvalidDecision,
    InvalidSequence,
    BoundsMismatch,
    InvalidNarrowingProof,
    DuplicateAuthorization,
    DuplicateIdempotencyKey,
    ResumeRequiresFreshPermit,
    TerminalExecution,
    RegistryUnavailable,
}

pub struct ContinuityVerifier {
    trusted: TrustedPermitIssuer,
}

impl ContinuityVerifier {
    pub fn new(trusted: TrustedPermitIssuer) -> Self {
        Self { trusted }
    }

    pub fn verify_json(
        &self,
        encoded: &str,
        now: DateTime<Utc>,
        expected: &ContinuityBindingContext,
    ) -> Result<(SignedArtifact, ContinuityEnforcementPayload), ContinuityError> {
        let artifact: SignedArtifact =
            serde_json::from_str(encoded).map_err(|_| ContinuityError::InvalidJson)?;
        self.verify_artifact(&artifact, now)?;
        let payload: ContinuityEnforcementPayload = serde_json::from_value(artifact.payload.clone())
            .map_err(|_| ContinuityError::InvalidPayload)?;
        self.validate_payload(&artifact, &payload, now, expected)?;
        Ok((artifact, payload))
    }

    pub fn verify(
        &self,
        artifact: &SignedArtifact,
        now: DateTime<Utc>,
        expected: &ContinuityBindingContext,
    ) -> Result<ContinuityEnforcementPayload, ContinuityError> {
        self.verify_artifact(artifact, now)?;
        let payload: ContinuityEnforcementPayload = serde_json::from_value(artifact.payload.clone())
            .map_err(|_| ContinuityError::InvalidPayload)?;
        self.validate_payload(artifact, &payload, now, expected)?;
        Ok(payload)
    }

    fn verify_artifact(
        &self,
        artifact: &SignedArtifact,
        now: DateTime<Utc>,
    ) -> Result<(), ContinuityError> {
        if artifact.artifact_type != "RACS_CONTINUITY_ENFORCEMENT" {
            return Err(ContinuityError::WrongArtifactType);
        }
        if artifact.schema_version != SCHEMA_VERSION {
            return Err(ContinuityError::UnsupportedSchema);
        }
        if artifact.profile_id != PROFILE_ID {
            return Err(ContinuityError::UnsupportedProfile);
        }
        if artifact.canonicalization != CANONICALIZATION {
            return Err(ContinuityError::UnsupportedCanonicalization);
        }
        if artifact.issuer_id != self.trusted.issuer_id {
            return Err(ContinuityError::WrongIssuer);
        }
        if artifact.issuer_role != self.trusted.issuer_role
            || artifact.issuer_role != "RACS_CONTINUITY_AUTHORITY"
        {
            return Err(ContinuityError::WrongIssuerRole);
        }
        if artifact.signature.algorithm != "Ed25519"
            || artifact.signature.key_id != self.trusted.key_id
        {
            return Err(ContinuityError::WrongKey);
        }
        if artifact.tenant_id != self.trusted.tenant_id {
            return Err(ContinuityError::WrongTenant);
        }
        if artifact.trust_domain != self.trusted.trust_domain {
            return Err(ContinuityError::WrongTrustDomain);
        }
        if !self.trusted.active {
            return Err(ContinuityError::InactiveKey);
        }

        let issued_at = parse_time(&artifact.issued_at)?;
        let expires_at = parse_time(&artifact.expires_at)?;
        if now < issued_at {
            return Err(ContinuityError::NotYetEffective);
        }
        if now >= expires_at {
            return Err(ContinuityError::Expired);
        }

        let canonical_payload =
            serde_jcs::to_vec(&artifact.payload).map_err(|_| ContinuityError::InvalidPayload)?;
        if sha256_digest(&canonical_payload) != artifact.payload_digest {
            return Err(ContinuityError::PayloadDigestMismatch);
        }

        let mut signature_input = artifact.clone();
        signature_input.signature.value.clear();
        let canonical_artifact =
            serde_jcs::to_vec(&signature_input).map_err(|_| ContinuityError::InvalidJson)?;
        let signature_bytes = decode_signature(&artifact.signature.value)?;
        let signature =
            Signature::from_slice(&signature_bytes).map_err(|_| ContinuityError::InvalidSignature)?;
        self.trusted
            .public_key
            .verify(&canonical_artifact, &signature)
            .map_err(|_| ContinuityError::InvalidSignature)
    }

    fn validate_payload(
        &self,
        artifact: &SignedArtifact,
        payload: &ContinuityEnforcementPayload,
        now: DateTime<Utc>,
        expected: &ContinuityBindingContext,
    ) -> Result<(), ContinuityError> {
        if payload.continuity_authorization_id != artifact.artifact_id {
            return Err(ContinuityError::InvalidPayload);
        }
        if payload.tenant_id != artifact.tenant_id || payload.tenant_id != expected.tenant_id {
            return Err(ContinuityError::WrongTenant);
        }

        for (name, value) in [
            ("continuity_authorization_id", payload.continuity_authorization_id.as_str()),
            ("session_id", payload.session_id.as_str()),
            ("execution_id", payload.execution_id.as_str()),
            ("execution_permit_id", payload.execution_permit_id.as_str()),
            ("commit_token_id", payload.commit_token_id.as_str()),
            ("continuity_decision_id", payload.continuity_decision_id.as_str()),
            ("decision", payload.decision.as_str()),
            ("verification_decision", payload.verification_decision.as_str()),
            ("verification_reason_code", payload.verification_reason_code.as_str()),
            ("idempotency_key", payload.idempotency_key.as_str()),
        ] {
            if value.is_empty() {
                return Err(ContinuityError::MissingBinding(name));
            }
        }
        for (name, value) in [
            ("execution_permit_digest", payload.execution_permit_digest.as_str()),
            ("commit_token_digest", payload.commit_token_digest.as_str()),
            ("continuity_decision_digest", payload.continuity_decision_digest.as_str()),
            ("current_bounds_digest", payload.current_bounds_digest.as_str()),
            ("effective_bounds_digest", payload.effective_bounds_digest.as_str()),
        ] {
            if !is_digest(value) {
                return Err(ContinuityError::MissingBinding(name));
            }
        }
        if let Some(proof) = &payload.narrowing_proof_digest {
            if !is_digest(proof) {
                return Err(ContinuityError::InvalidNarrowingProof);
            }
        }
        if payload.idempotency_key.len() < 8 || payload.continuity_sequence == 0 {
            return Err(ContinuityError::InvalidPayload);
        }

        for (name, actual, required) in [
            ("session_id", payload.session_id.as_str(), expected.session_id.as_str()),
            ("execution_id", payload.execution_id.as_str(), expected.execution_id.as_str()),
            (
                "execution_permit_id",
                payload.execution_permit_id.as_str(),
                expected.execution_permit_id.as_str(),
            ),
            (
                "execution_permit_digest",
                payload.execution_permit_digest.as_str(),
                expected.execution_permit_digest.as_str(),
            ),
            ("commit_token_id", payload.commit_token_id.as_str(), expected.commit_token_id.as_str()),
            (
                "commit_token_digest",
                payload.commit_token_digest.as_str(),
                expected.commit_token_digest.as_str(),
            ),
        ] {
            if actual != required {
                return Err(ContinuityError::BindingMismatch(name));
            }
        }

        if payload.verification_decision != "ACCEPT" {
            return Err(ContinuityError::VerificationRejected);
        }

        match payload.decision.as_str() {
            "CONTINUE" => {
                if payload.verification_reason_code != "ACCEPT"
                    || payload.current_bounds_digest != payload.effective_bounds_digest
                    || payload.narrowing_proof_digest.is_some()
                {
                    return Err(ContinuityError::InvalidVerificationReason);
                }
            }
            "MODIFY_RUNTIME_BOUNDS" => {
                if payload.verification_reason_code != "BOUNDS_NARROWED"
                    || payload.current_bounds_digest == payload.effective_bounds_digest
                    || payload.narrowing_proof_digest.is_none()
                {
                    return Err(ContinuityError::InvalidNarrowingProof);
                }
            }
            "PAUSE" | "STOP" | "REAUTHORIZE" | "ROLLBACK" | "HANDOVER" | "HALT" => {
                if payload.verification_reason_code != "ACCEPT"
                    || payload.current_bounds_digest != payload.effective_bounds_digest
                    || payload.narrowing_proof_digest.is_some()
                {
                    return Err(ContinuityError::InvalidVerificationReason);
                }
            }
            _ => return Err(ContinuityError::InvalidDecision),
        }

        let effective_at = parse_time(&payload.effective_at)?;
        let valid_until = parse_time(&payload.valid_until)?;
        if now < effective_at {
            return Err(ContinuityError::NotYetEffective);
        }
        if now >= valid_until {
            return Err(ContinuityError::Expired);
        }
        if valid_until > parse_time(&artifact.expires_at)? {
            return Err(ContinuityError::InvalidTime);
        }
        Ok(())
    }
}

pub struct DurableContinuityRegistry {
    path: PathBuf,
    authorization_ids: Mutex<HashSet<String>>,
    idempotency_keys: Mutex<HashSet<String>>,
    records_by_execution: Mutex<HashMap<String, ContinuityEnforcementRecord>>,
}

impl DurableContinuityRegistry {
    pub fn open(path: impl AsRef<Path>) -> Result<Self, ContinuityError> {
        let path = path.as_ref().to_path_buf();
        let mut authorization_ids = HashSet::new();
        let mut idempotency_keys = HashSet::new();
        let mut records_by_execution: HashMap<String, ContinuityEnforcementRecord> = HashMap::new();

        if path.exists() {
            let file = File::open(&path).map_err(|_| ContinuityError::RegistryUnavailable)?;
            for line in BufReader::new(file).lines() {
                let line = line.map_err(|_| ContinuityError::RegistryUnavailable)?;
                if line.trim().is_empty() {
                    continue;
                }
                let record: ContinuityEnforcementRecord = serde_json::from_str(&line)
                    .map_err(|_| ContinuityError::RegistryUnavailable)?;
                if !authorization_ids.insert(record.continuity_authorization_id.clone())
                    || !idempotency_keys.insert(record.idempotency_key.clone())
                {
                    return Err(ContinuityError::RegistryUnavailable);
                }
                match records_by_execution.get(&record.execution_id) {
                    Some(previous)
                        if record.continuity_sequence != previous.continuity_sequence + 1 =>
                    {
                        return Err(ContinuityError::RegistryUnavailable)
                    }
                    _ => {
                        records_by_execution.insert(record.execution_id.clone(), record);
                    }
                }
            }
        }

        Ok(Self {
            path,
            authorization_ids: Mutex::new(authorization_ids),
            idempotency_keys: Mutex::new(idempotency_keys),
            records_by_execution: Mutex::new(records_by_execution),
        })
    }

    pub fn enforce(
        &self,
        artifact: &SignedArtifact,
        payload: &ContinuityEnforcementPayload,
        expected: &ContinuityBindingContext,
        now: DateTime<Utc>,
    ) -> Result<(CoreContinuityDirective, ContinuityEnforcementRecord), ContinuityError> {
        let mut authorization_ids = self
            .authorization_ids
            .lock()
            .map_err(|_| ContinuityError::RegistryUnavailable)?;
        let mut idempotency_keys = self
            .idempotency_keys
            .lock()
            .map_err(|_| ContinuityError::RegistryUnavailable)?;
        let mut records = self
            .records_by_execution
            .lock()
            .map_err(|_| ContinuityError::RegistryUnavailable)?;

        if authorization_ids.contains(&artifact.artifact_id) {
            return Err(ContinuityError::DuplicateAuthorization);
        }
        if idempotency_keys.contains(&payload.idempotency_key) {
            return Err(ContinuityError::DuplicateIdempotencyKey);
        }

        let previous = records.get(&payload.execution_id).cloned();
        let (previous_state, expected_sequence, expected_bounds) = match &previous {
            Some(record) => (
                record.next_state,
                record.continuity_sequence + 1,
                record.effective_bounds_digest.as_str(),
            ),
            None => (
                ExecutionContinuityState::Active,
                1,
                expected.initial_bounds_digest.as_str(),
            ),
        };

        if payload.continuity_sequence != expected_sequence {
            return Err(ContinuityError::InvalidSequence);
        }
        if payload.current_bounds_digest != expected_bounds {
            return Err(ContinuityError::BoundsMismatch);
        }

        match previous_state {
            ExecutionContinuityState::Halted => return Err(ContinuityError::TerminalExecution),
            ExecutionContinuityState::Stopped if payload.decision != "HALT" => {
                return Err(ContinuityError::ResumeRequiresFreshPermit)
            }
            ExecutionContinuityState::Paused
                if !matches!(payload.decision.as_str(), "STOP" | "HALT") =>
            {
                return Err(ContinuityError::ResumeRequiresFreshPermit)
            }
            _ => {}
        }

        let (directive, next_state) = match payload.decision.as_str() {
            "CONTINUE" => (CoreContinuityDirective::Continue, previous_state),
            "MODIFY_RUNTIME_BOUNDS" => (
                CoreContinuityDirective::ApplyNarrowedBounds {
                    effective_bounds_digest: payload.effective_bounds_digest.clone(),
                },
                ExecutionContinuityState::BoundsModified,
            ),
            "PAUSE" | "REAUTHORIZE" | "ROLLBACK" | "HANDOVER" => {
                (CoreContinuityDirective::Pause, ExecutionContinuityState::Paused)
            }
            "STOP" => (CoreContinuityDirective::Stop, ExecutionContinuityState::Stopped),
            "HALT" => (CoreContinuityDirective::Halt, ExecutionContinuityState::Halted),
            _ => return Err(ContinuityError::InvalidDecision),
        };

        let record = ContinuityEnforcementRecord {
            continuity_authorization_id: artifact.artifact_id.clone(),
            tenant_id: payload.tenant_id.clone(),
            session_id: payload.session_id.clone(),
            execution_id: payload.execution_id.clone(),
            execution_permit_id: payload.execution_permit_id.clone(),
            commit_token_id: payload.commit_token_id.clone(),
            continuity_decision_id: payload.continuity_decision_id.clone(),
            continuity_sequence: payload.continuity_sequence,
            decision: payload.decision.clone(),
            previous_state,
            next_state,
            current_bounds_digest: payload.current_bounds_digest.clone(),
            effective_bounds_digest: payload.effective_bounds_digest.clone(),
            verification_reason_code: payload.verification_reason_code.clone(),
            enforced_at: timestamp(now),
            idempotency_key: payload.idempotency_key.clone(),
        };

        let encoded = serde_json::to_vec(&record).map_err(|_| ContinuityError::RegistryUnavailable)?;
        let mut file = OpenOptions::new()
            .create(true)
            .append(true)
            .open(&self.path)
            .map_err(|_| ContinuityError::RegistryUnavailable)?;
        file.write_all(&encoded)
            .map_err(|_| ContinuityError::RegistryUnavailable)?;
        file.write_all(b"\n")
            .map_err(|_| ContinuityError::RegistryUnavailable)?;
        file.sync_all()
            .map_err(|_| ContinuityError::RegistryUnavailable)?;

        authorization_ids.insert(artifact.artifact_id.clone());
        idempotency_keys.insert(payload.idempotency_key.clone());
        records.insert(payload.execution_id.clone(), record.clone());
        Ok((directive, record))
    }

    pub fn current_record(&self, execution_id: &str) -> Option<ContinuityEnforcementRecord> {
        self.records_by_execution
            .lock()
            .ok()
            .and_then(|records| records.get(execution_id).cloned())
    }
}

fn decode_signature(value: &str) -> Result<Vec<u8>, ContinuityError> {
    URL_SAFE_NO_PAD
        .decode(value.as_bytes())
        .or_else(|_| STANDARD.decode(value.as_bytes()))
        .map_err(|_| ContinuityError::InvalidSignature)
}

fn parse_time(value: &str) -> Result<DateTime<Utc>, ContinuityError> {
    DateTime::parse_from_rfc3339(value)
        .map(|value| value.with_timezone(&Utc))
        .map_err(|_| ContinuityError::InvalidTime)
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
        && value[7..]
            .bytes()
            .all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}
