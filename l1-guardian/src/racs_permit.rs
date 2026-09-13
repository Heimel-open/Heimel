use std::collections::HashSet;

use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use chrono::{DateTime, Utc};
use ed25519_dalek::{Signature, Signer, SigningKey, Verifier, VerifyingKey};
use serde::{Deserialize, Serialize};
use serde_json::Value;
use sha2::{Digest, Sha256};

const SCHEMA_VERSION: &str = "0.2.0";
const PROFILE_ID: &str = "racs-core-0.2";
const CANONICALIZATION: &str = "RACS-JCS-1";

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ArtifactSignature {
    pub algorithm: String,
    pub key_id: String,
    pub value: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SignedArtifact {
    pub artifact_type: String,
    pub schema_version: String,
    pub profile_id: String,
    pub artifact_id: String,
    pub tenant_id: String,
    pub trust_domain: String,
    pub issuer_id: String,
    pub issuer_role: String,
    pub issued_at: String,
    pub expires_at: String,
    pub payload: Value,
    pub payload_digest: String,
    pub canonicalization: String,
    pub signature: ArtifactSignature,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CoreExecutionPermitPayload {
    pub execution_id: String,
    pub action_id: String,
    pub tenant_id: String,
    pub clearance_id: String,
    pub clearance_digest: String,
    pub action_envelope_digest: String,
    pub connector_id: String,
    pub capability: String,
    pub target_digest: String,
    pub payload_digest: String,
    pub purpose_digest: String,
    pub authority_digest: String,
    pub policy_digest: String,
    pub evidence_digest: String,
    pub state_digest: String,
    pub valid_from: String,
    pub valid_until: String,
    pub replay_nonce: String,
    pub idempotency_key: String,
    pub reservation_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CommitTokenPayload {
    pub commit_token_id: String,
    pub execution_id: String,
    pub tenant_id: String,
    pub action_id: String,
    pub action_envelope_digest: String,
    pub clearance_id: String,
    pub clearance_digest: String,
    pub execution_permit_id: String,
    pub execution_permit_digest: String,
    pub connector_id: String,
    pub capability: String,
    pub target_digest: String,
    pub payload_digest: String,
    pub reservation_id: String,
    pub issued_at: String,
    pub valid_until: String,
    pub single_use: bool,
    pub consumption_registry_ref: String,
}

#[derive(Debug, Clone)]
pub struct TrustedPermitIssuer {
    pub issuer_id: String,
    pub issuer_role: String,
    pub key_id: String,
    pub tenant_id: String,
    pub trust_domain: String,
    pub public_key: VerifyingKey,
    pub active: bool,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum PermitError {
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
    NotYetValid,
    Expired,
    PayloadDigestMismatch,
    InvalidSignature,
    InvalidPayload,
    MissingBinding(&'static str),
    ReplayDetected,
    InvalidTokenValidity,
}

pub struct PermitVerifier {
    trusted: TrustedPermitIssuer,
}

impl PermitVerifier {
    pub fn new(trusted: TrustedPermitIssuer) -> Self {
        Self { trusted }
    }

    pub fn verify_json(
        &self,
        encoded: &str,
        now: DateTime<Utc>,
    ) -> Result<(SignedArtifact, CoreExecutionPermitPayload), PermitError> {
        let artifact: SignedArtifact = serde_json::from_str(encoded).map_err(|_| PermitError::InvalidJson)?;
        self.verify(&artifact, now)?;
        let payload: CoreExecutionPermitPayload =
            serde_json::from_value(artifact.payload.clone()).map_err(|_| PermitError::InvalidPayload)?;
        self.validate_payload(&artifact, &payload, now)?;
        Ok((artifact, payload))
    }

    pub fn verify(&self, artifact: &SignedArtifact, now: DateTime<Utc>) -> Result<(), PermitError> {
        if artifact.artifact_type != "CORE_EXECUTION_PERMIT" {
            return Err(PermitError::WrongArtifactType);
        }
        if artifact.schema_version != SCHEMA_VERSION {
            return Err(PermitError::UnsupportedSchema);
        }
        if artifact.profile_id != PROFILE_ID {
            return Err(PermitError::UnsupportedProfile);
        }
        if artifact.canonicalization != CANONICALIZATION {
            return Err(PermitError::UnsupportedCanonicalization);
        }
        if artifact.issuer_id != self.trusted.issuer_id {
            return Err(PermitError::WrongIssuer);
        }
        if artifact.issuer_role != self.trusted.issuer_role
            || artifact.issuer_role != "PLATFORM_PERMIT_ISSUER"
        {
            return Err(PermitError::WrongIssuerRole);
        }
        if artifact.signature.algorithm != "Ed25519" || artifact.signature.key_id != self.trusted.key_id {
            return Err(PermitError::WrongKey);
        }
        if artifact.tenant_id != self.trusted.tenant_id {
            return Err(PermitError::WrongTenant);
        }
        if artifact.trust_domain != self.trusted.trust_domain {
            return Err(PermitError::WrongTrustDomain);
        }
        if !self.trusted.active {
            return Err(PermitError::InactiveKey);
        }

        let issued_at = parse_time(&artifact.issued_at)?;
        let expires_at = parse_time(&artifact.expires_at)?;
        if now < issued_at {
            return Err(PermitError::NotYetValid);
        }
        if now >= expires_at {
            return Err(PermitError::Expired);
        }

        let canonical_payload = serde_jcs::to_vec(&artifact.payload).map_err(|_| PermitError::InvalidPayload)?;
        if sha256_digest(&canonical_payload) != artifact.payload_digest {
            return Err(PermitError::PayloadDigestMismatch);
        }

        let mut signature_input = artifact.clone();
        signature_input.signature.value.clear();
        let canonical_artifact =
            serde_jcs::to_vec(&signature_input).map_err(|_| PermitError::InvalidJson)?;
        let signature_bytes = BASE64
            .decode(artifact.signature.value.as_bytes())
            .map_err(|_| PermitError::InvalidSignature)?;
        let signature = Signature::from_slice(&signature_bytes).map_err(|_| PermitError::InvalidSignature)?;
        self.trusted
            .public_key
            .verify(&canonical_artifact, &signature)
            .map_err(|_| PermitError::InvalidSignature)
    }

    fn validate_payload(
        &self,
        artifact: &SignedArtifact,
        payload: &CoreExecutionPermitPayload,
        now: DateTime<Utc>,
    ) -> Result<(), PermitError> {
        if payload.tenant_id != artifact.tenant_id {
            return Err(PermitError::WrongTenant);
        }
        for (name, value) in [
            ("execution_id", payload.execution_id.as_str()),
            ("action_id", payload.action_id.as_str()),
            ("clearance_id", payload.clearance_id.as_str()),
            ("connector_id", payload.connector_id.as_str()),
            ("capability", payload.capability.as_str()),
            ("reservation_id", payload.reservation_id.as_str()),
            ("replay_nonce", payload.replay_nonce.as_str()),
            ("idempotency_key", payload.idempotency_key.as_str()),
        ] {
            if value.is_empty() {
                return Err(PermitError::MissingBinding(name));
            }
        }
        for (name, value) in [
            ("clearance_digest", payload.clearance_digest.as_str()),
            ("action_envelope_digest", payload.action_envelope_digest.as_str()),
            ("target_digest", payload.target_digest.as_str()),
            ("payload_digest", payload.payload_digest.as_str()),
            ("purpose_digest", payload.purpose_digest.as_str()),
            ("authority_digest", payload.authority_digest.as_str()),
            ("policy_digest", payload.policy_digest.as_str()),
            ("evidence_digest", payload.evidence_digest.as_str()),
            ("state_digest", payload.state_digest.as_str()),
        ] {
            if !is_digest(value) {
                return Err(PermitError::MissingBinding(name));
            }
        }
        if payload.replay_nonce.len() < 16 || payload.idempotency_key.len() < 8 {
            return Err(PermitError::InvalidPayload);
        }
        let valid_from = parse_time(&payload.valid_from)?;
        let valid_until = parse_time(&payload.valid_until)?;
        if now < valid_from {
            return Err(PermitError::NotYetValid);
        }
        if now >= valid_until {
            return Err(PermitError::Expired);
        }
        Ok(())
    }
}

pub struct CommitTokenIssuer {
    signing_key: SigningKey,
    issuer_id: String,
    key_id: String,
    trust_domain: String,
    consumption_registry_ref: String,
    issued_permits: HashSet<String>,
}

impl CommitTokenIssuer {
    pub fn new(
        signing_key: SigningKey,
        issuer_id: impl Into<String>,
        key_id: impl Into<String>,
        trust_domain: impl Into<String>,
        consumption_registry_ref: impl Into<String>,
    ) -> Self {
        Self {
            signing_key,
            issuer_id: issuer_id.into(),
            key_id: key_id.into(),
            trust_domain: trust_domain.into(),
            consumption_registry_ref: consumption_registry_ref.into(),
            issued_permits: HashSet::new(),
        }
    }

    pub fn issue(
        &mut self,
        permit: &SignedArtifact,
        payload: &CoreExecutionPermitPayload,
        commit_token_id: &str,
        now: DateTime<Utc>,
        valid_until: DateTime<Utc>,
    ) -> Result<SignedArtifact, PermitError> {
        if commit_token_id.is_empty() {
            return Err(PermitError::MissingBinding("commit_token_id"));
        }
        if self.issued_permits.contains(&permit.artifact_id) {
            return Err(PermitError::ReplayDetected);
        }
        let permit_expiry = parse_time(&payload.valid_until)?;
        if valid_until <= now || valid_until > permit_expiry {
            return Err(PermitError::InvalidTokenValidity);
        }

        let permit_bytes = serde_jcs::to_vec(permit).map_err(|_| PermitError::InvalidJson)?;
        let token_payload = CommitTokenPayload {
            commit_token_id: commit_token_id.to_owned(),
            execution_id: payload.execution_id.clone(),
            tenant_id: payload.tenant_id.clone(),
            action_id: payload.action_id.clone(),
            action_envelope_digest: payload.action_envelope_digest.clone(),
            clearance_id: payload.clearance_id.clone(),
            clearance_digest: payload.clearance_digest.clone(),
            execution_permit_id: permit.artifact_id.clone(),
            execution_permit_digest: sha256_digest(&permit_bytes),
            connector_id: payload.connector_id.clone(),
            capability: payload.capability.clone(),
            target_digest: payload.target_digest.clone(),
            payload_digest: payload.payload_digest.clone(),
            reservation_id: payload.reservation_id.clone(),
            issued_at: timestamp(now),
            valid_until: timestamp(valid_until),
            single_use: true,
            consumption_registry_ref: self.consumption_registry_ref.clone(),
        };
        let payload_value = serde_json::to_value(token_payload).map_err(|_| PermitError::InvalidPayload)?;
        let payload_bytes = serde_jcs::to_vec(&payload_value).map_err(|_| PermitError::InvalidPayload)?;
        let mut artifact = SignedArtifact {
            artifact_type: "COMMIT_TOKEN".to_owned(),
            schema_version: SCHEMA_VERSION.to_owned(),
            profile_id: PROFILE_ID.to_owned(),
            artifact_id: commit_token_id.to_owned(),
            tenant_id: payload.tenant_id.clone(),
            trust_domain: self.trust_domain.clone(),
            issuer_id: self.issuer_id.clone(),
            issuer_role: "CORE_COMMIT_TOKEN_ISSUER".to_owned(),
            issued_at: timestamp(now),
            expires_at: timestamp(valid_until),
            payload: payload_value,
            payload_digest: sha256_digest(&payload_bytes),
            canonicalization: CANONICALIZATION.to_owned(),
            signature: ArtifactSignature {
                algorithm: "Ed25519".to_owned(),
                key_id: self.key_id.clone(),
                value: String::new(),
            },
        };
        let signing_bytes = serde_jcs::to_vec(&artifact).map_err(|_| PermitError::InvalidJson)?;
        artifact.signature.value = BASE64.encode(self.signing_key.sign(&signing_bytes).to_bytes());
        self.issued_permits.insert(permit.artifact_id.clone());
        Ok(artifact)
    }
}

fn parse_time(value: &str) -> Result<DateTime<Utc>, PermitError> {
    DateTime::parse_from_rfc3339(value)
        .map(|value| value.with_timezone(&Utc))
        .map_err(|_| PermitError::InvalidTime)
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
        && value[7..].bytes().all(|byte| byte.is_ascii_hexdigit() && !byte.is_ascii_uppercase())
}

#[cfg(test)]
mod tests {
    use super::*;
    use chrono::TimeZone;

    fn digest(ch: char) -> String {
        format!("sha256:{}", ch.to_string().repeat(64))
    }

    fn signed_permit(now: DateTime<Utc>) -> (SignedArtifact, SigningKey, CoreExecutionPermitPayload) {
        let signing_key = SigningKey::from_bytes(&[7u8; 32]);
        let payload = CoreExecutionPermitPayload {
            execution_id: "exec-1".into(),
            action_id: "act-1".into(),
            tenant_id: "tenant-1".into(),
            clearance_id: "clr-1".into(),
            clearance_digest: digest('1'),
            action_envelope_digest: digest('2'),
            connector_id: "connector.erp".into(),
            capability: "invoice.create".into(),
            target_digest: digest('3'),
            payload_digest: digest('4'),
            purpose_digest: digest('5'),
            authority_digest: digest('6'),
            policy_digest: digest('7'),
            evidence_digest: digest('8'),
            state_digest: digest('9'),
            valid_from: timestamp(now),
            valid_until: timestamp(now + chrono::Duration::minutes(5)),
            replay_nonce: "nonce-0123456789".into(),
            idempotency_key: "idem-12345678".into(),
            reservation_id: "reservation-1".into(),
        };
        let payload_value = serde_json::to_value(&payload).unwrap();
        let payload_bytes = serde_jcs::to_vec(&payload_value).unwrap();
        let mut artifact = SignedArtifact {
            artifact_type: "CORE_EXECUTION_PERMIT".into(),
            schema_version: SCHEMA_VERSION.into(),
            profile_id: PROFILE_ID.into(),
            artifact_id: "permit-1".into(),
            tenant_id: "tenant-1".into(),
            trust_domain: "tenant-1:test".into(),
            issuer_id: "platform:test".into(),
            issuer_role: "PLATFORM_PERMIT_ISSUER".into(),
            issued_at: timestamp(now),
            expires_at: timestamp(now + chrono::Duration::minutes(5)),
            payload: payload_value,
            payload_digest: sha256_digest(&payload_bytes),
            canonicalization: CANONICALIZATION.into(),
            signature: ArtifactSignature {
                algorithm: "Ed25519".into(),
                key_id: "key:platform:1".into(),
                value: String::new(),
            },
        };
        let bytes = serde_jcs::to_vec(&artifact).unwrap();
        artifact.signature.value = BASE64.encode(signing_key.sign(&bytes).to_bytes());
        (artifact, signing_key, payload)
    }

    #[test]
    fn verifies_permit_and_issues_single_token() {
        let now = Utc.with_ymd_and_hms(2026, 7, 14, 18, 0, 0).unwrap();
        let (permit, platform_key, payload) = signed_permit(now);
        let trusted = TrustedPermitIssuer {
            issuer_id: "platform:test".into(),
            issuer_role: "PLATFORM_PERMIT_ISSUER".into(),
            key_id: "key:platform:1".into(),
            tenant_id: "tenant-1".into(),
            trust_domain: "tenant-1:test".into(),
            public_key: platform_key.verifying_key(),
            active: true,
        };
        PermitVerifier::new(trusted).verify(&permit, now).unwrap();

        let mut issuer = CommitTokenIssuer::new(
            SigningKey::from_bytes(&[9u8; 32]),
            "core:test",
            "key:core:1",
            "tenant-1:test",
            "consumption:test",
        );
        let token = issuer
            .issue(
                &permit,
                &payload,
                "token-1",
                now,
                now + chrono::Duration::seconds(30),
            )
            .unwrap();
        assert_eq!(token.artifact_type, "COMMIT_TOKEN");
        assert_eq!(token.payload["single_use"], true);
        assert_eq!(token.payload["target_digest"], digest('3'));
        assert_eq!(token.payload["payload_digest"], digest('4'));

        assert_eq!(
            issuer.issue(
                &permit,
                &payload,
                "token-2",
                now,
                now + chrono::Duration::seconds(30),
            ),
            Err(PermitError::ReplayDetected)
        );
    }

    #[test]
    fn rejects_tampered_payload() {
        let now = Utc.with_ymd_and_hms(2026, 7, 14, 18, 0, 0).unwrap();
        let (mut permit, platform_key, _) = signed_permit(now);
        permit.payload["connector_id"] = Value::String("connector.other".into());
        let trusted = TrustedPermitIssuer {
            issuer_id: "platform:test".into(),
            issuer_role: "PLATFORM_PERMIT_ISSUER".into(),
            key_id: "key:platform:1".into(),
            tenant_id: "tenant-1".into(),
            trust_domain: "tenant-1:test".into(),
            public_key: platform_key.verifying_key(),
            active: true,
        };
        assert_eq!(
            PermitVerifier::new(trusted).verify(&permit, now),
            Err(PermitError::PayloadDigestMismatch)
        );
    }

    #[test]
    fn rejects_inactive_key() {
        let now = Utc.with_ymd_and_hms(2026, 7, 14, 18, 0, 0).unwrap();
        let (permit, platform_key, _) = signed_permit(now);
        let trusted = TrustedPermitIssuer {
            issuer_id: "platform:test".into(),
            issuer_role: "PLATFORM_PERMIT_ISSUER".into(),
            key_id: "key:platform:1".into(),
            tenant_id: "tenant-1".into(),
            trust_domain: "tenant-1:test".into(),
            public_key: platform_key.verifying_key(),
            active: false,
        };
        assert_eq!(
            PermitVerifier::new(trusted).verify(&permit, now),
            Err(PermitError::InactiveKey)
        );
    }
}
