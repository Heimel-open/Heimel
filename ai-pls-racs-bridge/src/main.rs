#![forbid(unsafe_code)]

use std::io::{self, Read, Write};
use std::path::PathBuf;
use std::time::{SystemTime, UNIX_EPOCH};

use ai_pls_golden_path::DurablePermitConsumptionRegistry;
use ai_pls_racs_bridge::{BridgeError, RacsGoldenPathBridge};
use base64::{engine::general_purpose::STANDARD as BASE64, Engine};
use chrono::{DateTime, TimeZone, Utc};
use ed25519_dalek::VerifyingKey;
use l1_guardian::server::racs_cancellation::DurableInvalidationRegistry;
use l1_guardian::server::racs_permit::{SignedArtifact, TrustedPermitIssuer};
use serde::Deserialize;

#[derive(Debug, Deserialize)]
struct CliRequest {
    permit: SignedArtifact,
    trusted_issuer: TrustedIssuerRequest,
    now_epoch_ms: Option<u64>,
    revocation_registry_path: Option<PathBuf>,
    consumption_registry_path: PathBuf,
}

#[derive(Debug, Deserialize)]
struct TrustedIssuerRequest {
    issuer_id: String,
    issuer_role: String,
    key_id: String,
    tenant_id: String,
    trust_domain: String,
    public_key_base64: String,
    active: bool,
}

fn main() {
    if let Err(err) = run() {
        let payload = serde_json::json!({
            "ok": false,
            "error": err,
        });
        let _ = writeln!(io::stdout(), "{payload}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), String> {
    let mut input = String::new();
    io::stdin()
        .read_to_string(&mut input)
        .map_err(|e| format!("stdin_read_error:{e}"))?;

    let request: CliRequest =
        serde_json::from_str(&input).map_err(|e| format!("invalid_request:{e}"))?;
    let trusted = decode_trusted_issuer(request.trusted_issuer)?;
    let now = epoch_ms_to_datetime(request.now_epoch_ms.unwrap_or_else(now_epoch_ms));

    let effector_id = permit_effector_id(&request.permit);
    let consumption_registry =
        DurablePermitConsumptionRegistry::open(&request.consumption_registry_path)
            .map_err(|e| format!("consumption_registry_open:{e:?}"))?;
    let result = if let Some(path) = request.revocation_registry_path {
        let registry =
            DurableInvalidationRegistry::open(path).map_err(|e| format!("registry_open:{e:?}"))?;
        let mut bridge = RacsGoldenPathBridge::with_revocation_view(
            trusted,
            RuntimeEffector::new(effector_id),
            consumption_registry,
            registry,
        );
        bridge.process(&request.permit, now)
    } else {
        let mut bridge = RacsGoldenPathBridge::new(
            trusted,
            RuntimeEffector::new(effector_id),
            consumption_registry,
        );
        bridge.process(&request.permit, now)
    };

    match result {
        Ok(result) => {
            let payload = serde_json::json!({
                "ok": true,
                "outcome": format!("{:?}", result.outcome),
                "binding_valid": result.binding_valid,
                "replay_free": result.replay_free,
                "not_expired": result.not_expired,
                "execution_allowed": result.receipt.execution_allowed,
                "receipt": {
                    "receipt_id": result.receipt.receipt_id,
                    "permit_id": result.receipt.permit_id,
                    "action_envelope_digest": result.receipt.action_envelope_digest,
                    "clearance_id": result.receipt.clearance_id,
                    "effector_id": result.receipt.effector_id,
                    "replay_nonce": result.receipt.replay_nonce,
                    "consumption_record_id": result.receipt.consumption_record_id,
                    "execution_attempted": result.receipt.execution_attempted,
                    "effect_applied": result.receipt.effect_applied,
                    "effect_digest": result.receipt.effect_digest,
                    "failure_reason": result.receipt.failure_reason,
                    "core_state": format!("{:?}", result.receipt.core_state),
                    "sequence": result.receipt.sequence,
                    "timestamp": result.receipt.timestamp,
                }
            });
            writeln!(io::stdout(), "{payload}").map_err(|e| format!("stdout_write_error:{e}"))?;
            Ok(())
        }
        Err(BridgeError::Invalidated) => {
            let payload = serde_json::json!({
                "ok": false,
                "error": "invalidated",
            });
            writeln!(io::stdout(), "{payload}").map_err(|e| format!("stdout_write_error:{e}"))?;
            Ok(())
        }
        Err(BridgeError::Permit(err)) => Err(format!("permit_error:{err:?}")),
        Err(BridgeError::InvalidTime) => Err("invalid_time".to_owned()),
        Err(BridgeError::InvalidPayload) => Err("invalid_payload".to_owned()),
    }
}

fn decode_trusted_issuer(input: TrustedIssuerRequest) -> Result<TrustedPermitIssuer, String> {
    let key_bytes = BASE64
        .decode(input.public_key_base64.as_bytes())
        .map_err(|e| format!("invalid_public_key_base64:{e}"))?;
    let bytes: [u8; 32] = key_bytes
        .as_slice()
        .try_into()
        .map_err(|_| "invalid_public_key_length".to_owned())?;
    let public_key =
        VerifyingKey::from_bytes(&bytes).map_err(|e| format!("invalid_public_key:{e}"))?;

    Ok(TrustedPermitIssuer {
        issuer_id: input.issuer_id,
        issuer_role: input.issuer_role,
        key_id: input.key_id,
        tenant_id: input.tenant_id,
        trust_domain: input.trust_domain,
        public_key,
        active: input.active,
    })
}

fn epoch_ms_to_datetime(epoch_ms: u64) -> DateTime<Utc> {
    Utc.timestamp_millis_opt(epoch_ms as i64)
        .single()
        .unwrap_or_else(|| Utc.timestamp_millis_opt(0).single().unwrap())
}

fn now_epoch_ms() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|duration| duration.as_millis() as u64)
        .unwrap_or(0)
}

fn permit_effector_id(permit: &SignedArtifact) -> String {
    permit
        .payload
        .as_object()
        .and_then(|obj| obj.get("connector_id"))
        .and_then(|value| value.as_str())
        .unwrap_or("connector.unknown")
        .to_owned()
}

struct RuntimeEffector {
    effector_id: String,
}

impl RuntimeEffector {
    fn new(effector_id: String) -> Self {
        Self { effector_id }
    }
}

impl ai_pls_golden_path::ExclusiveEffector for RuntimeEffector {
    fn effector_id(&self) -> &str {
        &self.effector_id
    }

    fn execute(
        &mut self,
        envelope: &ai_pls_golden_path::ActionEnvelope,
        _: &ai_pls_golden_path::ExecutionAuthorization,
    ) -> Result<ai_pls_golden_path::SideEffectRecord, ai_pls_golden_path::EffectorError> {
        Ok(ai_pls_golden_path::SideEffectRecord {
            effector_id: self.effector_id().to_owned(),
            effect_id: format!("effect-{}", envelope.envelope_id),
            effect_digest: "sha256:noop".to_owned(),
        })
    }
}
