use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use chrono::{Duration, TimeZone, Utc};
use ed25519_dalek::{Signer, SigningKey};
use l1_guardian::server::racs_continuity::{
    ContinuityBindingContext, ContinuityEnforcementPayload, ContinuityError,
    ContinuityVerifier, CoreContinuityDirective, DurableContinuityRegistry,
    ExecutionContinuityState,
};
use l1_guardian::server::racs_permit::{
    ArtifactSignature, SignedArtifact, TrustedPermitIssuer,
};
use l1_guardian::server::ValoExecutionServer;
use l1_guardian::ValoState;
use sha2::{Digest, Sha256};
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

fn digest(ch: char) -> String {
    format!("sha256:{}", ch.to_string().repeat(64))
}

fn context() -> ContinuityBindingContext {
    ContinuityBindingContext {
        tenant_id: "tenant-1".into(),
        session_id: "session-1".into(),
        execution_id: "exec-1".into(),
        execution_permit_id: "permit-1".into(),
        execution_permit_digest: digest('1'),
        commit_token_id: "token-1".into(),
        commit_token_digest: digest('2'),
        initial_bounds_digest: digest('3'),
    }
}

fn payload(
    authorization_id: &str,
    idempotency_key: &str,
    sequence: u64,
    decision: &str,
    reason: &str,
    current_bounds: String,
    effective_bounds: String,
    proof: Option<String>,
    now: chrono::DateTime<Utc>,
) -> ContinuityEnforcementPayload {
    ContinuityEnforcementPayload {
        continuity_authorization_id: authorization_id.into(),
        tenant_id: "tenant-1".into(),
        session_id: "session-1".into(),
        execution_id: "exec-1".into(),
        execution_permit_id: "permit-1".into(),
        execution_permit_digest: digest('1'),
        commit_token_id: "token-1".into(),
        commit_token_digest: digest('2'),
        continuity_decision_id: format!("decision-{sequence}"),
        continuity_decision_digest: digest('4'),
        continuity_sequence: sequence,
        decision: decision.into(),
        verification_decision: "ACCEPT".into(),
        verification_reason_code: reason.into(),
        current_bounds_digest: current_bounds,
        effective_bounds_digest: effective_bounds,
        narrowing_proof_digest: proof,
        effective_at: timestamp(now),
        valid_until: timestamp(now + Duration::minutes(5)),
        idempotency_key: idempotency_key.into(),
    }
}

fn sign(
    payload: &ContinuityEnforcementPayload,
    signing_key: &SigningKey,
    now: chrono::DateTime<Utc>,
) -> SignedArtifact {
    let payload_value = serde_json::to_value(payload).unwrap();
    let payload_bytes = serde_jcs::to_vec(&payload_value).unwrap();
    let mut artifact = SignedArtifact {
        artifact_type: "RACS_CONTINUITY_ENFORCEMENT".into(),
        schema_version: "0.2.0".into(),
        profile_id: "racs-core-0.2".into(),
        artifact_id: payload.continuity_authorization_id.clone(),
        tenant_id: payload.tenant_id.clone(),
        trust_domain: "tenant-1:test".into(),
        issuer_id: "racs:test".into(),
        issuer_role: "RACS_CONTINUITY_AUTHORITY".into(),
        issued_at: timestamp(now),
        expires_at: timestamp(now + Duration::minutes(5)),
        payload: payload_value,
        payload_digest: sha256_digest(&payload_bytes),
        canonicalization: "RACS-JCS-1".into(),
        signature: ArtifactSignature {
            algorithm: "Ed25519".into(),
            key_id: "key:racs:1".into(),
            value: String::new(),
        },
    };
    let bytes = serde_jcs::to_vec(&artifact).unwrap();
    artifact.signature.value = BASE64.encode(signing_key.sign(&bytes).to_bytes());
    artifact
}

fn verifier(signing_key: &SigningKey) -> ContinuityVerifier {
    ContinuityVerifier::new(TrustedPermitIssuer {
        issuer_id: "racs:test".into(),
        issuer_role: "RACS_CONTINUITY_AUTHORITY".into(),
        key_id: "key:racs:1".into(),
        tenant_id: "tenant-1".into(),
        trust_domain: "tenant-1:test".into(),
        public_key: signing_key.verifying_key(),
        active: true,
    })
}

fn registry_path(name: &str) -> PathBuf {
    let unique = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_nanos();
    std::env::temp_dir().join(format!(
        "racs-continuity-{name}-{}-{unique}.jsonl",
        std::process::id()
    ))
}

#[test]
fn verifies_modify_enforces_and_survives_reopen() {
    let now = Utc.with_ymd_and_hms(2026, 7, 28, 10, 0, 0).unwrap();
    let signing_key = SigningKey::from_bytes(&[21u8; 32]);
    let expected = context();
    let payload = payload(
        "continuity-1",
        "idem-continuity-1",
        1,
        "MODIFY_RUNTIME_BOUNDS",
        "BOUNDS_NARROWED",
        digest('3'),
        digest('5'),
        Some(digest('6')),
        now,
    );
    let artifact = sign(&payload, &signing_key, now);
    let verified = verifier(&signing_key)
        .verify(&artifact, now, &expected)
        .unwrap();

    let path = registry_path("modify");
    let registry = DurableContinuityRegistry::open(&path).unwrap();
    let (directive, record) = registry
        .enforce(&artifact, &verified, &expected, now)
        .unwrap();
    assert_eq!(
        directive,
        CoreContinuityDirective::ApplyNarrowedBounds {
            effective_bounds_digest: digest('5')
        }
    );
    assert_eq!(record.next_state, ExecutionContinuityState::BoundsModified);
    drop(registry);

    let reopened = DurableContinuityRegistry::open(&path).unwrap();
    let persisted = reopened.current_record("exec-1").unwrap();
    assert_eq!(persisted.continuity_sequence, 1);
    assert_eq!(persisted.effective_bounds_digest, digest('5'));
    let _ = std::fs::remove_file(path);
}

#[test]
fn rejects_replay_and_wrong_followup_bounds() {
    let now = Utc.with_ymd_and_hms(2026, 7, 28, 10, 0, 0).unwrap();
    let signing_key = SigningKey::from_bytes(&[22u8; 32]);
    let expected = context();
    let first = payload(
        "continuity-1",
        "idem-continuity-1",
        1,
        "MODIFY_RUNTIME_BOUNDS",
        "BOUNDS_NARROWED",
        digest('3'),
        digest('5'),
        Some(digest('6')),
        now,
    );
    let first_artifact = sign(&first, &signing_key, now);
    let path = registry_path("replay");
    let registry = DurableContinuityRegistry::open(&path).unwrap();
    registry
        .enforce(&first_artifact, &first, &expected, now)
        .unwrap();
    assert_eq!(
        registry.enforce(&first_artifact, &first, &expected, now),
        Err(ContinuityError::DuplicateAuthorization)
    );

    let second = payload(
        "continuity-2",
        "idem-continuity-2",
        2,
        "CONTINUE",
        "ACCEPT",
        digest('3'),
        digest('3'),
        None,
        now,
    );
    let second_artifact = sign(&second, &signing_key, now);
    assert_eq!(
        registry.enforce(&second_artifact, &second, &expected, now),
        Err(ContinuityError::BoundsMismatch)
    );
    let _ = std::fs::remove_file(path);
}

#[test]
fn continuity_cannot_resume_paused_execution() {
    let now = Utc.with_ymd_and_hms(2026, 7, 28, 10, 0, 0).unwrap();
    let signing_key = SigningKey::from_bytes(&[23u8; 32]);
    let expected = context();
    let pause = payload(
        "continuity-pause",
        "idem-pause-1",
        1,
        "PAUSE",
        "ACCEPT",
        digest('3'),
        digest('3'),
        None,
        now,
    );
    let pause_artifact = sign(&pause, &signing_key, now);
    let path = registry_path("pause");
    let registry = DurableContinuityRegistry::open(&path).unwrap();
    let (directive, _) = registry
        .enforce(&pause_artifact, &pause, &expected, now)
        .unwrap();
    assert_eq!(directive, CoreContinuityDirective::Pause);

    let resume = payload(
        "continuity-resume",
        "idem-resume-2",
        2,
        "CONTINUE",
        "ACCEPT",
        digest('3'),
        digest('3'),
        None,
        now,
    );
    let resume_artifact = sign(&resume, &signing_key, now);
    assert_eq!(
        registry.enforce(&resume_artifact, &resume, &expected, now),
        Err(ContinuityError::ResumeRequiresFreshPermit)
    );
    let _ = std::fs::remove_file(path);
}

#[test]
fn rejects_unaccepted_verification_and_tampering() {
    let now = Utc.with_ymd_and_hms(2026, 7, 28, 10, 0, 0).unwrap();
    let signing_key = SigningKey::from_bytes(&[24u8; 32]);
    let expected = context();
    let mut rejected = payload(
        "continuity-rejected",
        "idem-rejected-1",
        1,
        "CONTINUE",
        "ACCEPT",
        digest('3'),
        digest('3'),
        None,
        now,
    );
    rejected.verification_decision = "REJECT".into();
    let rejected_artifact = sign(&rejected, &signing_key, now);
    assert!(matches!(
        verifier(&signing_key).verify(&rejected_artifact, now, &expected),
        Err(ContinuityError::VerificationRejected)
    ));

    let valid = payload(
        "continuity-valid",
        "idem-valid-1",
        1,
        "CONTINUE",
        "ACCEPT",
        digest('3'),
        digest('3'),
        None,
        now,
    );
    let mut tampered = sign(&valid, &signing_key, now);
    tampered.payload["decision"] = serde_json::Value::String("HALT".into());
    assert!(matches!(
        verifier(&signing_key).verify(&tampered, now, &expected),
        Err(ContinuityError::PayloadDigestMismatch)
    ));
}

#[test]
fn halt_directive_uses_existing_global_halt_path() {
    let now = Utc.with_ymd_and_hms(2026, 7, 28, 10, 0, 0).unwrap();
    let signing_key = SigningKey::from_bytes(&[25u8; 32]);
    let expected = context();
    let halt = payload(
        "continuity-halt",
        "idem-halt-1",
        1,
        "HALT",
        "ACCEPT",
        digest('3'),
        digest('3'),
        None,
        now,
    );
    let halt_artifact = sign(&halt, &signing_key, now);
    let path = registry_path("halt");
    let registry = DurableContinuityRegistry::open(&path).unwrap();
    let (directive, record) = registry
        .enforce(&halt_artifact, &halt, &expected, now)
        .unwrap();
    assert_eq!(directive, CoreContinuityDirective::Halt);
    assert_eq!(record.next_state, ExecutionContinuityState::Halted);

    std::env::set_var("VALO_HSM_KEY", "test-key-for-continuity-enforcement");
    let mut server = ValoExecutionServer::new(5, 3, 20);
    assert_eq!(server.apply_racs_continuity_directive(&directive), ValoState::Halt);
    assert!(!server.is_running);
    assert_eq!(server.hmac_signature_vault.len(), 1);
    let _ = std::fs::remove_file(path);
}

fn timestamp(value: chrono::DateTime<Utc>) -> String {
    value.to_rfc3339_opts(chrono::SecondsFormat::AutoSi, true)
}

fn sha256_digest(data: &[u8]) -> String {
    format!("sha256:{:x}", Sha256::digest(data))
}
