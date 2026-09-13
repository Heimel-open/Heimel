use std::process::Command;
use std::time::{SystemTime, UNIX_EPOCH};

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

#[test]
fn cli_processes_verified_permit() {
    let now = Utc.with_ymd_and_hms(2026, 7, 14, 18, 0, 0).unwrap();
    let (permit, signing_key) = signed_permit(now);
    let permit_json = serde_json::to_value(&permit).unwrap();
    let trusted = serde_json::json!({
        "issuer_id": "platform:test",
        "issuer_role": "PLATFORM_PERMIT_ISSUER",
        "key_id": "key:platform:1",
        "tenant_id": "tenant-1",
        "trust_domain": "tenant-1:test",
        "public_key_base64": BASE64.encode(signing_key.verifying_key().to_bytes()),
        "active": true,
    });

    let request = serde_json::json!({
        "permit": permit_json,
        "trusted_issuer": trusted,
        "now_epoch_ms": now.timestamp_millis(),
        "revocation_registry_path": null,
        "consumption_registry_path": std::env::temp_dir().join(format!("cli-consumption-{}.jsonl", SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos())),
    });

    let binary = std::env::var("CARGO_BIN_EXE_ai-pls-racs-bridge")
        .or_else(|_| std::env::var("CARGO_BIN_EXE_ai_pls_racs_bridge"))
        .expect("cargo binary path");

    let output = Command::new(binary)
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .spawn()
        .and_then(|mut child| {
            use std::io::Write;
            let mut stdin = child.stdin.take().unwrap();
            stdin.write_all(request.to_string().as_bytes())?;
            drop(stdin);
            let output = child.wait_with_output()?;
            Ok(output)
        })
        .expect("bridge cli");

    assert!(
        output.status.success(),
        "stderr={}",
        String::from_utf8_lossy(&output.stderr)
    );
    let response: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(response["ok"], true);
    assert_eq!(response["execution_allowed"], true);
    assert_eq!(response["receipt"]["core_state"], "Normal");
    assert_eq!(response["receipt"]["effector_id"], "connector.erp");
    assert_eq!(response["receipt"]["replay_nonce"], "nonce-0123456789");
    assert_eq!(response["receipt"]["execution_attempted"], true);
    assert_eq!(response["receipt"]["effect_applied"], true);
}

#[test]
fn cli_blocks_revoked_permit() {
    let now = Utc.with_ymd_and_hms(2026, 7, 14, 18, 0, 0).unwrap();
    let (permit, signing_key) = signed_permit(now);
    let permit_json = serde_json::to_value(&permit).unwrap();
    let trusted = serde_json::json!({
        "issuer_id": "platform:test",
        "issuer_role": "PLATFORM_PERMIT_ISSUER",
        "key_id": "key:platform:1",
        "tenant_id": "tenant-1",
        "trust_domain": "tenant-1:test",
        "public_key_base64": BASE64.encode(signing_key.verifying_key().to_bytes()),
        "active": true,
    });

    let permit_payload = permit
        .payload
        .as_object()
        .expect("permit payload must be object");
    let permit_payload: CoreExecutionPermitPayload =
        serde_json::from_value(serde_json::Value::Object(permit_payload.clone())).unwrap();

    let cancellation_payload = CancellationAuthorizationPayload {
        cancellation_authorization_id: "cancel-1".into(),
        cancellation_request_id: "request-1".into(),
        tenant_id: permit.tenant_id.clone(),
        task_id: permit_payload.action_id.clone(),
        execution_id: permit_payload.execution_id.clone(),
        execution_permit_id: permit.artifact_id.clone(),
        execution_permit_digest: {
            let bytes = serde_jcs::to_vec(&permit).unwrap();
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
    let signing_key = SigningKey::from_bytes(&[7u8; 32]);
    let mut cancellation_artifact = SignedArtifact {
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
    let bytes = serde_jcs::to_vec(&cancellation_artifact).unwrap();
    cancellation_artifact.signature.value = BASE64.encode(signing_key.sign(&bytes).to_bytes());

    let unique = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos();
    let registry_path = std::env::temp_dir().join(format!("ai-pls-racs-bridge-cli-{unique}.jsonl"));
    let registry = DurableInvalidationRegistry::open(&registry_path).expect("registry open");
    let verifier = CancellationVerifier::new(TrustedPermitIssuer {
        issuer_id: "reht:test".into(),
        issuer_role: "REHT_CANCELLATION_AUTHORITY".into(),
        key_id: "key:reht:1".into(),
        tenant_id: "tenant-1".into(),
        trust_domain: "tenant-1:test".into(),
        public_key: signing_key.verifying_key(),
        active: true,
    });
    let encoded = serde_json::to_string(&cancellation_artifact).expect("encode cancellation");
    let (_, verified_payload) = verifier
        .verify_json(&encoded, now)
        .expect("cancellation verify");
    registry
        .invalidate(&cancellation_artifact, &verified_payload, now)
        .expect("invalidate");

    let request = serde_json::json!({
        "permit": permit_json,
        "trusted_issuer": trusted,
        "now_epoch_ms": now.timestamp_millis(),
        "revocation_registry_path": registry_path,
        "consumption_registry_path": std::env::temp_dir().join(format!("cli-consumption-revoked-{}.jsonl", unique)),
    });

    let binary = std::env::var("CARGO_BIN_EXE_ai-pls-racs-bridge")
        .or_else(|_| std::env::var("CARGO_BIN_EXE_ai_pls_racs_bridge"))
        .expect("cargo binary path");

    let output = Command::new(binary)
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .spawn()
        .and_then(|mut child| {
            use std::io::Write;
            let mut stdin = child.stdin.take().unwrap();
            stdin.write_all(request.to_string().as_bytes())?;
            drop(stdin);
            let output = child.wait_with_output()?;
            Ok(output)
        })
        .expect("bridge cli");

    assert!(
        output.status.success(),
        "stderr={}",
        String::from_utf8_lossy(&output.stderr)
    );
    let response: serde_json::Value = serde_json::from_slice(&output.stdout).unwrap();
    assert_eq!(response["ok"], false);
    assert_eq!(response["error"], "invalidated");

    let _ = std::fs::remove_file(registry_path);
}
