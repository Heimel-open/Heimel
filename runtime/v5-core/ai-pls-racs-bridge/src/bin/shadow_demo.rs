#![forbid(unsafe_code)]

use std::env;
use std::fs;
use std::time::{SystemTime, UNIX_EPOCH};

use ai_pls_golden_path::DurablePermitConsumptionRegistry;
use ai_pls_racs_bridge::RacsGoldenPathBridge;
use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use chrono::{TimeZone, Utc};
use ed25519_dalek::{Signer, SigningKey};
use l1_guardian::server::racs_cancellation::{
    CancellationAuthorizationPayload, CancellationVerifier, DurableInvalidationRegistry,
};
use l1_guardian::server::racs_permit::{
    ArtifactSignature, CoreExecutionPermitPayload, SignedArtifact, TrustedPermitIssuer,
};
use sha2::{Digest, Sha256};

fn main() {
    if let Err(err) = run() {
        eprintln!("[SHADOW] ERROR: {err}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let now = Utc.with_ymd_and_hms(2026, 7, 14, 18, 0, 0).unwrap();
    let (permit, signing_key) = signed_permit(now);
    let trusted = trusted_issuer(&signing_key);

    let mode = env::args().nth(1).unwrap_or_else(|| "shadow".to_owned());
    let consumption_path = env::temp_dir().join(format!(
        "ai-pls-consumption-demo-{}.jsonl",
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|e| format!("clock:{e}"))?
            .as_nanos()
    ));
    let consumption = DurablePermitConsumptionRegistry::open(&consumption_path)
        .map_err(|e| format!("consumption_open:{e:?}"))?;
    if mode == "shadow" {
        let mut bridge = RacsGoldenPathBridge::new(trusted.clone(), PanicEffector, consumption);
        let receipt = bridge
            .shadow(&permit, now)
            .map_err(|e| format!("shadow:{e:?}"))?;
        ensure(receipt.would_execute, "shadow should report would_execute")?;
        ensure(!receipt.effect_applied, "shadow must not apply effects")?;
        ensure(
            fs::metadata(&consumption_path)
                .map_err(|e| e.to_string())?
                .len()
                == 0,
            "shadow must not consume nonce",
        )?;
        println!(
            "[SHADOW] execution_allowed={} would_execute={} effect_applied=false shadow_mode=true",
            receipt.execution_allowed, receipt.would_execute
        );
        let _ = fs::remove_file(consumption_path);
        println!("ALL PASS");
        return Ok(());
    }
    ensure(mode == "integration", "mode must be shadow or integration")?;
    let mut bridge =
        RacsGoldenPathBridge::new(trusted.clone(), RecordingEffector::default(), consumption);
    let allow = bridge
        .process(&permit, now)
        .map_err(|e| format!("allow:{e:?}"))?;
    ensure(
        allow.receipt.execution_allowed,
        "integration path should execute",
    )?;
    ensure(
        allow.receipt.effect_applied,
        "integration path should apply exactly one effect",
    )?;
    println!(
        "[INTEGRATION] outcome={:?} execution_allowed=true effect_applied=true",
        allow.outcome
    );

    let permit_payload = permit
        .payload
        .as_object()
        .ok_or_else(|| "permit payload must be object".to_owned())?;
    let permit_payload: CoreExecutionPermitPayload =
        serde_json::from_value(serde_json::Value::Object(permit_payload.clone()))
            .map_err(|e| format!("permit_payload:{e}"))?;

    let cancellation = cancellation_authorization(now, &permit, &permit_payload)?;
    let registry_path = env::temp_dir().join(format!(
        "ai-pls-racs-shadow-{}.jsonl",
        SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|e| format!("clock:{e}"))?
            .as_nanos()
    ));
    let registry = DurableInvalidationRegistry::open(&registry_path)
        .map_err(|e| format!("registry_open:{e:?}"))?;
    let encoded =
        serde_json::to_string(&cancellation.0).map_err(|e| format!("encode_cancel:{e}"))?;
    let verifier = CancellationVerifier::new(cancellation.1);
    let (_, verified_payload) = verifier
        .verify_json(&encoded, now)
        .map_err(|e| format!("verify_cancel:{e:?}"))?;
    registry
        .invalidate(&cancellation.0, &verified_payload, now)
        .map_err(|e| format!("invalidate:{e:?}"))?;

    let mut blocked_bridge = RacsGoldenPathBridge::with_revocation_view(
        trusted,
        RecordingEffector::default(),
        DurablePermitConsumptionRegistry::open(env::temp_dir().join(format!(
            "ai-pls-consumption-blocked-{}.jsonl",
            SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos()
        )))
        .map_err(|e| format!("consumption_open:{e:?}"))?,
        registry,
    );
    let blocked = blocked_bridge.process(&permit, now);
    match blocked {
        Err(ai_pls_racs_bridge::BridgeError::Invalidated) => {
            println!(
                "[SHADOW] revoke outcome=blocked execution_allowed=false effect_applied=false"
            );
        }
        Err(err) => return Err(format!("blocked:{err:?}")),
        Ok(result) => {
            ensure(
                !result.receipt.execution_allowed,
                "revoked path must be blocked",
            )?;
            ensure(
                !result.receipt.effect_applied,
                "revoked path must not apply effects",
            )?;
            println!(
                "[SHADOW] revoke outcome={:?} execution_allowed={} effect_applied={}",
                result.outcome, result.receipt.execution_allowed, result.receipt.effect_applied
            );
        }
    }

    let _ = fs::remove_file(registry_path);
    println!("ALL PASS");
    Ok(())
}

fn ensure(condition: bool, message: &str) -> Result<(), String> {
    if condition {
        Ok(())
    } else {
        Err(message.to_owned())
    }
}

fn digest(ch: char) -> String {
    format!("sha256:{}", ch.to_string().repeat(64))
}

fn timestamp(value: chrono::DateTime<Utc>) -> String {
    value.to_rfc3339_opts(chrono::SecondsFormat::AutoSi, true)
}

fn signed_permit(now: chrono::DateTime<Utc>) -> (SignedArtifact, SigningKey) {
    let signing_key = SigningKey::from_bytes(&[7u8; 32]);
    let mut payload = CoreExecutionPermitPayload {
        execution_id: "exec-1".into(),
        action_id: "act-1".into(),
        tenant_id: "tenant-1".into(),
        clearance_id: "clr-1".into(),
        clearance_digest: digest('1'),
        action_envelope_digest: String::new(),
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
    let envelope = ai_pls_golden_path::ActionEnvelope {
        envelope_id: payload.action_id.clone(),
        purpose_digest: payload.purpose_digest.clone(),
        authority_digest: payload.authority_digest.clone(),
        target_digest: payload.target_digest.clone(),
        payload_digest: payload.payload_digest.clone(),
        replay_nonce: payload.replay_nonce.clone(),
        valid_until_epoch_ms: (now + chrono::Duration::minutes(5)).timestamp_millis() as u64,
    };
    payload.action_envelope_digest = envelope.digest();
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
        payload_digest: format!("sha256:{:x}", Sha256::digest(&payload_bytes)),
        canonicalization: "RACS-JCS-1".into(),
        signature: ArtifactSignature {
            algorithm: "Ed25519".into(),
            key_id: "key:platform:1".into(),
            value: String::new(),
        },
    };
    let bytes = serde_jcs::to_vec(&artifact).unwrap();
    artifact.signature.value = BASE64.encode(signing_key.sign(&bytes).to_bytes());
    (artifact, signing_key)
}

fn trusted_issuer(signing_key: &SigningKey) -> TrustedPermitIssuer {
    TrustedPermitIssuer {
        issuer_id: "platform:test".into(),
        issuer_role: "PLATFORM_PERMIT_ISSUER".into(),
        key_id: "key:platform:1".into(),
        tenant_id: "tenant-1".into(),
        trust_domain: "tenant-1:test".into(),
        public_key: signing_key.verifying_key(),
        active: true,
    }
}

fn cancellation_authorization(
    now: chrono::DateTime<Utc>,
    permit: &SignedArtifact,
    payload: &CoreExecutionPermitPayload,
) -> Result<(SignedArtifact, TrustedPermitIssuer), String> {
    let signing_key = SigningKey::from_bytes(&[9u8; 32]);
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
    Ok((
        artifact,
        TrustedPermitIssuer {
            issuer_id: "reht:test".into(),
            issuer_role: "REHT_CANCELLATION_AUTHORITY".into(),
            key_id: "key:reht:1".into(),
            tenant_id: permit.tenant_id.clone(),
            trust_domain: permit.trust_domain.clone(),
            public_key: signing_key.verifying_key(),
            active: true,
        },
    ))
}

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
        envelope: &ai_pls_golden_path::ActionEnvelope,
        _: &ai_pls_golden_path::ExecutionAuthorization,
    ) -> Result<ai_pls_golden_path::SideEffectRecord, ai_pls_golden_path::EffectorError> {
        self.calls.push(envelope.envelope_id.clone());
        Ok(ai_pls_golden_path::SideEffectRecord {
            effector_id: self.effector_id().to_owned(),
            effect_id: format!("effect-{}", self.calls.len()),
            effect_digest: "sha256:noop".to_owned(),
        })
    }
}

struct PanicEffector;
impl ai_pls_golden_path::ExclusiveEffector for PanicEffector {
    fn effector_id(&self) -> &str {
        "connector.erp"
    }
    fn execute(
        &mut self,
        _: &ai_pls_golden_path::ActionEnvelope,
        _: &ai_pls_golden_path::ExecutionAuthorization,
    ) -> Result<ai_pls_golden_path::SideEffectRecord, ai_pls_golden_path::EffectorError> {
        panic!("shadow mode attempted an effector call")
    }
}
