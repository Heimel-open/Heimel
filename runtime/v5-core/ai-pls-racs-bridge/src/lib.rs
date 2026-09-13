#![forbid(unsafe_code)]

use ai_pls_golden_path::{
    ActionEnvelope, DurablePermitConsumptionRegistry, GoldenExecutionPath, GoldenPathResult,
    PermitCommit, ShadowReceipt, SignedClearanceEnvelope,
};
use chrono::{DateTime, Utc};
use l1_guardian::server::racs_cancellation::DurableInvalidationRegistry;
use l1_guardian::server::racs_permit::{
    CoreExecutionPermitPayload, PermitError, PermitVerifier, SignedArtifact, TrustedPermitIssuer,
};
#[cfg(test)]
use sha2::Digest;

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum BridgeError {
    Permit(PermitError),
    Invalidated,
    InvalidTime,
    InvalidPayload,
}

pub trait PermitInvalidationView {
    fn is_permit_invalidated(&self, permit_id: &str) -> bool;
}

impl PermitInvalidationView for () {
    fn is_permit_invalidated(&self, _permit_id: &str) -> bool {
        false
    }
}

impl PermitInvalidationView for DurableInvalidationRegistry {
    fn is_permit_invalidated(&self, permit_id: &str) -> bool {
        DurableInvalidationRegistry::is_permit_invalidated(self, permit_id)
    }
}

pub struct RacsGoldenPathBridge<E: ai_pls_golden_path::ExclusiveEffector, R = ()> {
    verifier: PermitVerifier,
    effector_path: GoldenExecutionPath<E>,
    revocation_view: R,
}

impl<E: ai_pls_golden_path::ExclusiveEffector> RacsGoldenPathBridge<E, ()> {
    pub fn new(
        trusted: TrustedPermitIssuer,
        effector: E,
        registry: DurablePermitConsumptionRegistry,
    ) -> Self {
        Self {
            verifier: PermitVerifier::new(trusted),
            effector_path: GoldenExecutionPath::new(effector, registry),
            revocation_view: (),
        }
    }
}

impl<E: ai_pls_golden_path::ExclusiveEffector, R> RacsGoldenPathBridge<E, R> {
    pub fn with_revocation_view(
        trusted: TrustedPermitIssuer,
        effector: E,
        registry: DurablePermitConsumptionRegistry,
        revocation_view: R,
    ) -> Self {
        Self {
            verifier: PermitVerifier::new(trusted),
            effector_path: GoldenExecutionPath::new(effector, registry),
            revocation_view,
        }
    }

    pub fn process(
        &mut self,
        permit: &SignedArtifact,
        now: DateTime<Utc>,
    ) -> Result<GoldenPathResult, BridgeError>
    where
        R: PermitInvalidationView,
    {
        if self
            .revocation_view
            .is_permit_invalidated(&permit.artifact_id)
        {
            return Err(BridgeError::Invalidated);
        }

        let payload = self.verify_payload(permit, now)?;
        let envelope = self.build_envelope(&payload)?;
        if payload.action_envelope_digest != envelope.digest() {
            return Err(BridgeError::InvalidPayload);
        }
        let clearance = self.build_clearance(&payload, &envelope)?;
        let commit = PermitCommit {
            permit_id: permit.artifact_id.clone(),
            execution_id: payload.execution_id.clone(),
            action_id: payload.action_id.clone(),
            connector_id: payload.connector_id.clone(),
            capability: payload.capability.clone(),
            idempotency_key: payload.idempotency_key.clone(),
            reservation_id: payload.reservation_id.clone(),
        };
        Ok(self.effector_path.process(
            &commit,
            &envelope,
            &clearance,
            now.timestamp_millis() as u64,
        ))
    }

    pub fn shadow(
        &mut self,
        permit: &SignedArtifact,
        now: DateTime<Utc>,
    ) -> Result<ShadowReceipt, BridgeError>
    where
        R: PermitInvalidationView,
    {
        if self
            .revocation_view
            .is_permit_invalidated(&permit.artifact_id)
        {
            return Err(BridgeError::Invalidated);
        }
        let payload = self.verify_payload(permit, now)?;
        let envelope = self.build_envelope(&payload)?;
        if payload.action_envelope_digest != envelope.digest() {
            return Err(BridgeError::InvalidPayload);
        }
        let clearance = self.build_clearance(&payload, &envelope)?;
        let commit = PermitCommit {
            permit_id: permit.artifact_id.clone(),
            execution_id: payload.execution_id,
            action_id: payload.action_id,
            connector_id: payload.connector_id,
            capability: payload.capability,
            idempotency_key: payload.idempotency_key,
            reservation_id: payload.reservation_id,
        };
        Ok(self.effector_path.shadow(
            &commit,
            &envelope,
            &clearance,
            now.timestamp_millis() as u64,
        ))
    }

    fn verify_payload(
        &self,
        permit: &SignedArtifact,
        now: DateTime<Utc>,
    ) -> Result<CoreExecutionPermitPayload, BridgeError> {
        let encoded = serde_json::to_string(permit).map_err(|_| BridgeError::InvalidPayload)?;
        let (_, payload) = self
            .verifier
            .verify_json(&encoded, now)
            .map_err(BridgeError::Permit)?;
        Ok(payload)
    }

    fn build_envelope(
        &self,
        payload: &CoreExecutionPermitPayload,
    ) -> Result<ActionEnvelope, BridgeError> {
        Ok(ActionEnvelope {
            envelope_id: payload.action_id.clone(),
            purpose_digest: payload.purpose_digest.clone(),
            authority_digest: payload.authority_digest.clone(),
            target_digest: payload.target_digest.clone(),
            payload_digest: payload.payload_digest.clone(),
            replay_nonce: payload.replay_nonce.clone(),
            valid_until_epoch_ms: parse_ms(&payload.valid_until)?,
        })
    }

    fn build_clearance(
        &self,
        payload: &CoreExecutionPermitPayload,
        envelope: &ActionEnvelope,
    ) -> Result<SignedClearanceEnvelope, BridgeError> {
        let issued_at = parse_ms(&payload.valid_from)?;
        let valid_until = parse_ms(&payload.valid_until)?;
        let clearance = SignedClearanceEnvelope {
            clearance_id: payload.clearance_id.clone(),
            clearance: ai_pls_golden_path::Clearance::Clear,
            action_envelope_digest: envelope.digest(),
            effector_id: payload.connector_id.clone(),
            issued_at_epoch_ms: issued_at,
            valid_until_epoch_ms: valid_until,
            binding_digest: String::new(),
        };

        Ok(SignedClearanceEnvelope {
            binding_digest: clearance.expected_binding_digest(),
            ..clearance
        })
    }
}

fn parse_ms(value: &str) -> Result<u64, BridgeError> {
    let parsed = DateTime::parse_from_rfc3339(value).map_err(|_| BridgeError::InvalidTime)?;
    Ok(parsed.with_timezone(&Utc).timestamp_millis() as u64)
}

#[cfg(test)]
fn digest_hex(bytes: &[u8]) -> String {
    let digest = sha2::Sha256::digest(bytes);
    let mut out = String::with_capacity(64);
    for byte in digest {
        out.push_str(&format!("{byte:02x}"));
    }
    format!("sha256:{out}")
}

#[cfg(test)]
mod tests {
    use super::*;
    use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
    use chrono::TimeZone;
    use ed25519_dalek::{Signer, SigningKey};
    use l1_guardian::server::racs_cancellation::{
        CancellationAuthorizationPayload, CancellationVerifier,
    };
    use l1_guardian::server::racs_permit::{
        ArtifactSignature, CoreExecutionPermitPayload, SignedArtifact,
    };
    use sha2::{Digest, Sha256};
    use std::time::{SystemTime, UNIX_EPOCH};

    #[derive(Default)]
    struct RecordingEffector {
        calls: Vec<String>,
    }

    impl ai_pls_golden_path::ExclusiveEffector for RecordingEffector {
        fn effector_id(&self) -> &str {
            "connector.erp"
        }

        fn execute(
            &mut self,
            envelope: &ActionEnvelope,
            _: &ai_pls_golden_path::ExecutionAuthorization,
        ) -> Result<ai_pls_golden_path::SideEffectRecord, ai_pls_golden_path::EffectorError>
        {
            self.calls.push(envelope.envelope_id.clone());
            Ok(ai_pls_golden_path::SideEffectRecord {
                effector_id: self.effector_id().to_owned(),
                effect_id: format!("effect-{}", self.calls.len()),
                effect_digest: digest_hex(envelope.envelope_id.as_bytes()),
            })
        }
    }

    fn consumption_registry() -> DurablePermitConsumptionRegistry {
        let path = std::env::temp_dir().join(format!(
            "racs-consumption-{}.jsonl",
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        DurablePermitConsumptionRegistry::open(path).unwrap()
    }

    fn digest(ch: char) -> String {
        format!("sha256:{}", ch.to_string().repeat(64))
    }

    fn timestamp(value: DateTime<Utc>) -> String {
        value.to_rfc3339_opts(chrono::SecondsFormat::AutoSi, true)
    }

    fn signed_permit(now: DateTime<Utc>) -> (SignedArtifact, TrustedPermitIssuer) {
        let signing_key = SigningKey::from_bytes(&[7u8; 32]);
        let envelope_digest = digest_hex(
            format!(
                "envelope_id={}|purpose_digest={}|authority_digest={}|target_digest={}|payload_digest={}|replay_nonce={}|valid_until_epoch_ms={}",
                "act-1",
                digest('5'),
                digest('6'),
                digest('3'),
                digest('4'),
                "nonce-0123456789",
                (now + chrono::Duration::minutes(5)).timestamp_millis() as u64,
            )
            .as_bytes(),
        );
        let payload = CoreExecutionPermitPayload {
            execution_id: "exec-1".into(),
            action_id: "act-1".into(),
            tenant_id: "tenant-1".into(),
            clearance_id: "clr-1".into(),
            clearance_digest: digest('1'),
            action_envelope_digest: envelope_digest,
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
            schema_version: "0.2.0".into(),
            profile_id: "racs-core-0.2".into(),
            artifact_id: "permit-1".into(),
            tenant_id: "tenant-1".into(),
            trust_domain: "tenant-1:test".into(),
            issuer_id: "platform:test".into(),
            issuer_role: "PLATFORM_PERMIT_ISSUER".into(),
            issued_at: timestamp(now),
            expires_at: timestamp(now + chrono::Duration::minutes(5)),
            payload: payload_value,
            payload_digest: {
                let digest = Sha256::digest(&payload_bytes);
                format!("sha256:{digest:x}")
            },
            canonicalization: "RACS-JCS-1".into(),
            signature: ArtifactSignature {
                algorithm: "Ed25519".into(),
                key_id: "key:platform:1".into(),
                value: String::new(),
            },
        };
        let bytes = serde_jcs::to_vec(&artifact).unwrap();
        artifact.signature.value = BASE64.encode(signing_key.sign(&bytes).to_bytes());

        let trusted = TrustedPermitIssuer {
            issuer_id: "platform:test".into(),
            issuer_role: "PLATFORM_PERMIT_ISSUER".into(),
            key_id: "key:platform:1".into(),
            tenant_id: "tenant-1".into(),
            trust_domain: "tenant-1:test".into(),
            public_key: signing_key.verifying_key(),
            active: true,
        };

        (artifact, trusted)
    }

    fn signed_cancellation(
        now: DateTime<Utc>,
        permit: &SignedArtifact,
        payload: &CoreExecutionPermitPayload,
    ) -> (
        SignedArtifact,
        TrustedPermitIssuer,
        CancellationAuthorizationPayload,
    ) {
        let signing_key = SigningKey::from_bytes(&[7u8; 32]);
        let cancellation_payload = CancellationAuthorizationPayload {
            cancellation_authorization_id: "cancel-1".into(),
            cancellation_request_id: "request-1".into(),
            tenant_id: permit.tenant_id.clone(),
            task_id: payload.action_id.clone(),
            execution_id: payload.execution_id.clone(),
            execution_permit_id: permit.artifact_id.clone(),
            execution_permit_digest: {
                let bytes = serde_jcs::to_vec(permit).unwrap();
                format!("sha256:{:x}", Sha256::digest(&bytes))
            },
            commit_token_id: "token-1".into(),
            commit_token_digest: digest('a'),
            source_revocation_event_id: "revoke-1".into(),
            decision: "HALT".into(),
            effective_at: timestamp(now),
            valid_until: timestamp(now + chrono::Duration::minutes(5)),
            evidence_refs: vec!["evidence-1".into()],
            idempotency_key: "idem-cancel-1".into(),
        };
        let payload_value = serde_json::to_value(&cancellation_payload).unwrap();
        let payload_bytes = serde_jcs::to_vec(&payload_value).unwrap();
        let mut artifact = SignedArtifact {
            artifact_type: "CANCELLATION_AUTHORIZATION".into(),
            schema_version: "0.2.0".into(),
            profile_id: "racs-core-0.2".into(),
            artifact_id: cancellation_payload.cancellation_authorization_id.clone(),
            tenant_id: permit.tenant_id.clone(),
            trust_domain: permit.trust_domain.clone(),
            issuer_id: "reht:test".into(),
            issuer_role: "REHT_CANCELLATION_AUTHORITY".into(),
            issued_at: timestamp(now),
            expires_at: timestamp(now + chrono::Duration::minutes(5)),
            payload: payload_value,
            payload_digest: format!("sha256:{:x}", Sha256::digest(&payload_bytes)),
            canonicalization: "RACS-JCS-1".into(),
            signature: ArtifactSignature {
                algorithm: "Ed25519".into(),
                key_id: "key:reht:1".into(),
                value: String::new(),
            },
        };
        let bytes = serde_jcs::to_vec(&artifact).unwrap();
        artifact.signature.value = BASE64.encode(signing_key.sign(&bytes).to_bytes());

        let trusted = TrustedPermitIssuer {
            issuer_id: "reht:test".into(),
            issuer_role: "REHT_CANCELLATION_AUTHORITY".into(),
            key_id: "key:reht:1".into(),
            tenant_id: permit.tenant_id.clone(),
            trust_domain: permit.trust_domain.clone(),
            public_key: signing_key.verifying_key(),
            active: true,
        };

        (artifact, trusted, cancellation_payload)
    }

    #[test]
    fn verified_permit_executes_through_golden_path() {
        let now = Utc.with_ymd_and_hms(2026, 7, 14, 18, 0, 0).unwrap();
        let (permit, trusted) = signed_permit(now);
        let mut bridge = RacsGoldenPathBridge::new(
            trusted,
            RecordingEffector::default(),
            consumption_registry(),
        );

        let result = bridge.process(&permit, now).expect("permit should execute");

        assert!(result.receipt.execution_allowed);
        assert!(result.receipt.effect_applied);
        assert_eq!(result.receipt.effector_id, "connector.erp");
    }

    #[test]
    fn invalidated_permit_is_blocked_before_execution() {
        let now = Utc.with_ymd_and_hms(2026, 7, 14, 18, 0, 0).unwrap();
        let (permit, trusted) = signed_permit(now);
        struct AlwaysInvalidated;

        impl PermitInvalidationView for AlwaysInvalidated {
            fn is_permit_invalidated(&self, _permit_id: &str) -> bool {
                true
            }
        }

        let mut bridge = RacsGoldenPathBridge::with_revocation_view(
            trusted,
            RecordingEffector::default(),
            consumption_registry(),
            AlwaysInvalidated,
        );

        let err = bridge
            .process(&permit, now)
            .expect_err("permit should be blocked by revocation view");
        assert_eq!(err, BridgeError::Invalidated);
    }

    #[test]
    fn file_backed_registry_blocks_revoked_permit() {
        let now = Utc.with_ymd_and_hms(2026, 7, 14, 18, 0, 0).unwrap();
        let (permit, trusted) = signed_permit(now);
        let permit_payload = permit
            .payload
            .as_object()
            .expect("permit payload must be object");
        let permit_payload: CoreExecutionPermitPayload =
            serde_json::from_value(serde_json::Value::Object(permit_payload.clone())).unwrap();

        let (cancel_artifact, cancel_trusted, _cancel_payload) =
            signed_cancellation(now, &permit, &permit_payload);

        let unique = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_nanos();
        let registry_path = std::env::temp_dir().join(format!("ai-pls-racs-bridge-{unique}.jsonl"));
        let registry = DurableInvalidationRegistry::open(&registry_path).expect("registry open");
        let verifier = CancellationVerifier::new(cancel_trusted);
        let encoded = serde_json::to_string(&cancel_artifact).expect("encode cancellation");
        let (_, verified_payload) = verifier
            .verify_json(&encoded, now)
            .expect("cancellation verify");
        registry
            .invalidate(&cancel_artifact, &verified_payload, now)
            .expect("invalidate");

        let mut bridge = RacsGoldenPathBridge::with_revocation_view(
            trusted,
            RecordingEffector::default(),
            consumption_registry(),
            registry,
        );
        let err = bridge
            .process(&permit, now)
            .expect_err("revoked permit must be blocked");
        assert_eq!(err, BridgeError::Invalidated);

        let _ = std::fs::remove_file(registry_path);
    }

    #[test]
    fn permit_and_binding_mutations_fail_closed() {
        let now = Utc.with_ymd_and_hms(2026, 7, 14, 18, 0, 0).unwrap();
        let (permit, trusted) = signed_permit(now);

        for field in [
            "payload_digest",
            "target_digest",
            "connector_id",
            "capability",
            "authority_digest",
            "policy_digest",
            "evidence_digest",
            "state_digest",
        ] {
            let mut changed = permit.clone();
            changed.payload[field] = if field.ends_with("_digest") {
                serde_json::Value::String(digest('f'))
            } else {
                serde_json::Value::String("changed.binding".into())
            };
            let mut bridge = RacsGoldenPathBridge::new(
                trusted.clone(),
                RecordingEffector::default(),
                consumption_registry(),
            );
            assert!(
                bridge.process(&changed, now).is_err(),
                "mutation of {field} must fail closed"
            );
        }

        for mutation in [
            "signature",
            "issuer",
            "issuer_role",
            "tenant",
            "trust_domain",
        ] {
            let mut changed = permit.clone();
            match mutation {
                "signature" => changed.signature.value = "invalid".into(),
                "issuer" => changed.issuer_id = "untrusted".into(),
                "issuer_role" => changed.issuer_role = "UNTRUSTED_ROLE".into(),
                "tenant" => changed.tenant_id = "other-tenant".into(),
                "trust_domain" => changed.trust_domain = "other-domain".into(),
                _ => unreachable!(),
            }
            let mut bridge = RacsGoldenPathBridge::new(
                trusted.clone(),
                RecordingEffector::default(),
                consumption_registry(),
            );
            assert!(
                bridge.process(&changed, now).is_err(),
                "{mutation} mutation must fail closed"
            );
        }

        let mut inactive = trusted.clone();
        inactive.active = false;
        let mut bridge = RacsGoldenPathBridge::new(
            inactive,
            RecordingEffector::default(),
            consumption_registry(),
        );
        assert!(bridge.process(&permit, now).is_err());

        let mut bridge = RacsGoldenPathBridge::new(
            trusted.clone(),
            RecordingEffector::default(),
            consumption_registry(),
        );
        assert!(bridge
            .process(&permit, now - chrono::Duration::minutes(1))
            .is_err());
        let mut bridge = RacsGoldenPathBridge::new(
            trusted,
            RecordingEffector::default(),
            consumption_registry(),
        );
        assert!(bridge
            .process(&permit, now + chrono::Duration::minutes(6))
            .is_err());
    }
}
