#![forbid(unsafe_code)]

pub use ai_pls_core::{
    AiPlsCore, Clearance, CoreState, EnforcementReason, EnforcementResult, ExecutionSignal,
    HumanResetAuthorization, ResetError,
};
use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use std::collections::HashSet;
use std::fs::{File, OpenOptions};
use std::io::{BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use std::sync::Mutex;

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ActionEnvelope {
    pub envelope_id: String,
    pub purpose_digest: String,
    pub authority_digest: String,
    pub target_digest: String,
    pub payload_digest: String,
    pub replay_nonce: String,
    pub valid_until_epoch_ms: u64,
}

impl ActionEnvelope {
    pub fn digest(&self) -> String {
        digest_hex(&format!(
            "envelope_id={}|purpose_digest={}|authority_digest={}|target_digest={}|payload_digest={}|replay_nonce={}|valid_until_epoch_ms={}",
            self.envelope_id, self.purpose_digest, self.authority_digest, self.target_digest,
            self.payload_digest, self.replay_nonce, self.valid_until_epoch_ms
        ).into_bytes())
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SignedClearanceEnvelope {
    pub clearance_id: String,
    pub clearance: Clearance,
    pub action_envelope_digest: String,
    pub effector_id: String,
    pub issued_at_epoch_ms: u64,
    pub valid_until_epoch_ms: u64,
    pub binding_digest: String,
}

impl SignedClearanceEnvelope {
    pub fn expected_binding_digest(&self) -> String {
        digest_hex(format!(
            "clearance_id={}|clearance={}|action_envelope_digest={}|effector_id={}|issued_at_epoch_ms={}|valid_until_epoch_ms={}",
            self.clearance_id, self.clearance as u8, self.action_envelope_digest, self.effector_id,
            self.issued_at_epoch_ms, self.valid_until_epoch_ms
        ).as_bytes())
    }

    pub fn binding_valid(&self, digest: &str, effector: &str, now: u64) -> bool {
        self.action_envelope_digest == digest
            && self.effector_id == effector
            && self.issued_at_epoch_ms <= now
            && self.valid_until_epoch_ms > now
            && self.binding_digest == self.expected_binding_digest()
    }
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PermitCommit {
    pub permit_id: String,
    pub execution_id: String,
    pub action_id: String,
    pub connector_id: String,
    pub capability: String,
    pub idempotency_key: String,
    pub reservation_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct PermitConsumptionRecord {
    pub record_id: String,
    pub permit_id: String,
    pub execution_id: String,
    pub action_id: String,
    pub action_envelope_digest: String,
    pub clearance_id: String,
    pub connector_id: String,
    pub capability: String,
    pub target_digest: String,
    pub payload_digest: String,
    pub replay_nonce: String,
    pub idempotency_key: String,
    pub reservation_id: String,
    pub consumed_at: u64,
    pub effector_id: String,
    pub previous_record_digest: String,
    pub record_digest: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum RegistryError {
    Io,
    Corrupt,
    Inconsistent,
    AlreadyConsumed,
    Unavailable,
}

#[derive(Debug)]
struct RegistryState {
    file: File,
    records: Vec<PermitConsumptionRecord>,
    nonces: HashSet<String>,
    permits: HashSet<String>,
    idempotency_keys: HashSet<String>,
}

#[derive(Debug)]
pub struct DurablePermitConsumptionRegistry {
    path: PathBuf,
    state: Mutex<RegistryState>,
}

impl DurablePermitConsumptionRegistry {
    pub fn open(path: impl AsRef<Path>) -> Result<Self, RegistryError> {
        let path = path.as_ref().to_owned();
        let read = OpenOptions::new()
            .read(true)
            .create(true)
            .append(true)
            .open(&path)
            .map_err(|_| RegistryError::Unavailable)?;
        let mut records = Vec::new();
        let mut nonces = HashSet::new();
        let mut permits = HashSet::new();
        let mut idempotency_keys = HashSet::new();
        let mut previous = String::new();
        for line in BufReader::new(read.try_clone().map_err(|_| RegistryError::Io)?).lines() {
            let line = line.map_err(|_| RegistryError::Corrupt)?;
            if line.trim().is_empty() {
                return Err(RegistryError::Corrupt);
            }
            let record: PermitConsumptionRecord =
                serde_json::from_str(&line).map_err(|_| RegistryError::Corrupt)?;
            if record.previous_record_digest != previous
                || record.record_digest != record_digest(&record)
                || !nonces.insert(record.replay_nonce.clone())
                || !permits.insert(record.permit_id.clone())
                || !idempotency_keys.insert(record.idempotency_key.clone())
            {
                return Err(RegistryError::Inconsistent);
            }
            previous = record.record_digest.clone();
            records.push(record);
        }
        Ok(Self {
            path,
            state: Mutex::new(RegistryState {
                file: read,
                records,
                nonces,
                permits,
                idempotency_keys,
            }),
        })
    }

    pub fn path(&self) -> &Path {
        &self.path
    }

    pub fn records(&self) -> Result<Vec<PermitConsumptionRecord>, RegistryError> {
        self.state
            .lock()
            .map(|s| s.records.clone())
            .map_err(|_| RegistryError::Unavailable)
    }

    /// Performs the replay checks and durable append under one lock. `sync_all`
    /// completes before the caller can obtain an execution authorization.
    pub fn reserve_and_consume(
        &self,
        permit: &PermitCommit,
        envelope: &ActionEnvelope,
        clearance: &SignedClearanceEnvelope,
        effector_id: &str,
        now: u64,
    ) -> Result<PermitConsumptionRecord, RegistryError> {
        let mut state = self.state.lock().map_err(|_| RegistryError::Unavailable)?;
        if state.nonces.contains(&envelope.replay_nonce)
            || state.permits.contains(&permit.permit_id)
            || state.idempotency_keys.contains(&permit.idempotency_key)
        {
            return Err(RegistryError::AlreadyConsumed);
        }
        let previous_record_digest = state
            .records
            .last()
            .map(|r| r.record_digest.clone())
            .unwrap_or_default();
        let mut record = PermitConsumptionRecord {
            record_id: digest_hex(
                format!(
                    "{}|{}|{}|{}",
                    permit.permit_id, permit.execution_id, envelope.replay_nonce, now
                )
                .as_bytes(),
            ),
            permit_id: permit.permit_id.clone(),
            execution_id: permit.execution_id.clone(),
            action_id: permit.action_id.clone(),
            action_envelope_digest: envelope.digest(),
            clearance_id: clearance.clearance_id.clone(),
            connector_id: permit.connector_id.clone(),
            capability: permit.capability.clone(),
            target_digest: envelope.target_digest.clone(),
            payload_digest: envelope.payload_digest.clone(),
            replay_nonce: envelope.replay_nonce.clone(),
            idempotency_key: permit.idempotency_key.clone(),
            reservation_id: permit.reservation_id.clone(),
            consumed_at: now,
            effector_id: effector_id.to_owned(),
            previous_record_digest,
            record_digest: String::new(),
        };
        record.record_digest = record_digest(&record);
        let encoded = serde_json::to_vec(&record).map_err(|_| RegistryError::Corrupt)?;
        state
            .file
            .write_all(&encoded)
            .and_then(|_| state.file.write_all(b"\n"))
            .and_then(|_| state.file.sync_all())
            .map_err(|_| RegistryError::Unavailable)?;
        state.nonces.insert(record.replay_nonce.clone());
        state.permits.insert(record.permit_id.clone());
        state
            .idempotency_keys
            .insert(record.idempotency_key.clone());
        state.records.push(record.clone());
        Ok(record)
    }
}

fn record_digest(record: &PermitConsumptionRecord) -> String {
    let mut copy = record.clone();
    copy.record_digest.clear();
    digest_hex(&serde_json::to_vec(&copy).expect("serializable record"))
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct SideEffectRecord {
    pub effector_id: String,
    pub effect_id: String,
    pub effect_digest: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct EffectorError(pub String);

/// The authorization is constructible only inside this crate. This makes a
/// direct effector call fail closed at the type boundary.
pub struct ExecutionAuthorization {
    _private: (),
}

/// A consequence-bearing effector. Direct callers cannot forge the required
/// authorization:
///
/// ```compile_fail
/// use ai_pls_golden_path::{ActionEnvelope, ExclusiveEffector};
/// fn bypass<E: ExclusiveEffector>(effector: &mut E, action: &ActionEnvelope) {
///     let authorization = ai_pls_golden_path::ExecutionAuthorization { _private: () };
///     let _ = effector.execute(action, &authorization);
/// }
/// ```
pub trait ExclusiveEffector {
    fn effector_id(&self) -> &str;
    fn execute(
        &mut self,
        envelope: &ActionEnvelope,
        authorization: &ExecutionAuthorization,
    ) -> Result<SideEffectRecord, EffectorError>;
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExecutionReceipt {
    pub receipt_id: String,
    pub permit_id: String,
    pub clearance_id: String,
    pub action_envelope_digest: String,
    pub effector_id: String,
    pub replay_nonce: String,
    pub consumption_record_id: String,
    pub execution_allowed: bool,
    pub execution_attempted: bool,
    pub effect_applied: bool,
    pub effect_digest: Option<String>,
    pub failure_reason: Option<String>,
    pub core_state: CoreState,
    pub sequence: u64,
    pub timestamp: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ShadowReceipt {
    pub execution_allowed: bool,
    pub would_execute: bool,
    pub effect_applied: bool,
    pub shadow_mode: bool,
    pub reason: String,
    pub permit_id: String,
    pub action_digest: String,
    pub binding_valid: bool,
    pub replay_free: bool,
    pub not_expired: bool,
    pub observed_at: u64,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum GoldenPathOutcome {
    Executed,
    Blocked,
    Attempted,
    Shadow,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct GoldenPathResult {
    pub outcome: GoldenPathOutcome,
    pub binding_valid: bool,
    pub replay_free: bool,
    pub not_expired: bool,
    pub enforcement: EnforcementResult,
    pub receipt: ExecutionReceipt,
    pub side_effect: Option<SideEffectRecord>,
}

pub struct GoldenExecutionPath<E: ExclusiveEffector> {
    core: AiPlsCore,
    effector: E,
    registry: DurablePermitConsumptionRegistry,
}

impl<E: ExclusiveEffector> GoldenExecutionPath<E> {
    pub fn new(effector: E, registry: DurablePermitConsumptionRegistry) -> Self {
        Self {
            core: AiPlsCore::new(),
            effector,
            registry,
        }
    }

    pub fn core_state(&self) -> CoreState {
        self.core.state()
    }

    /// Lift a HALT using a reset-authorization token from the governance
    /// chain's human oversight. The token must be bound to this effector's
    /// identity and carry a valid canonical digest.
    pub fn human_reset(
        &mut self,
        token_json: &str,
    ) -> Result<EnforcementResult, ResetError> {
        let authorization = HumanResetAuthorization::from_verified_human_path(
            token_json,
            self.effector.effector_id(),
        )?;
        self.core.human_reset(authorization)
    }

    pub fn process(
        &mut self,
        permit: &PermitCommit,
        envelope: &ActionEnvelope,
        clearance: &SignedClearanceEnvelope,
        now: u64,
    ) -> GoldenPathResult {
        let digest = envelope.digest();
        let binding_valid = clearance.binding_valid(&digest, self.effector.effector_id(), now)
            && permit.action_id == envelope.envelope_id
            && permit.connector_id == self.effector.effector_id();
        let not_expired = envelope.valid_until_epoch_ms > now;
        let preflight_valid =
            binding_valid && not_expired && clearance.clearance == Clearance::Clear;
        let consumption = if preflight_valid {
            self.registry.reserve_and_consume(
                permit,
                envelope,
                clearance,
                self.effector.effector_id(),
                now,
            )
        } else {
            Err(RegistryError::Inconsistent)
        };
        let replay_free = !matches!(consumption, Err(RegistryError::AlreadyConsumed));
        let integrity = preflight_valid && consumption.is_ok();
        let enforcement = self.core.evaluate(ExecutionSignal {
            clearance: if integrity {
                clearance.clearance
            } else {
                Clearance::Invalid
            },
            envelope_integrity_valid: binding_valid,
            receipt_valid: consumption.is_ok(),
            context_valid: permit.action_id == envelope.envelope_id,
            not_expired,
            replay_free,
        });
        let mut attempted = false;
        let mut side_effect = None;
        let mut failure_reason = consumption
            .as_ref()
            .err()
            .map(|e| format!("registry:{e:?}"));
        if enforcement.execution_allowed {
            attempted = true;
            match self
                .effector
                .execute(envelope, &ExecutionAuthorization { _private: () })
            {
                Ok(effect) => side_effect = Some(effect),
                Err(error) => failure_reason = Some(error.0),
            }
        }
        let effect_applied = side_effect.is_some();
        let consumption_id = consumption
            .as_ref()
            .map(|r| r.record_id.clone())
            .unwrap_or_default();
        let receipt_id = digest_hex(
            format!(
                "{}|{}|{}|{}",
                permit.permit_id, consumption_id, enforcement.sequence, now
            )
            .as_bytes(),
        );
        let receipt = ExecutionReceipt {
            receipt_id,
            permit_id: permit.permit_id.clone(),
            clearance_id: clearance.clearance_id.clone(),
            action_envelope_digest: digest,
            effector_id: self.effector.effector_id().to_owned(),
            replay_nonce: envelope.replay_nonce.clone(),
            consumption_record_id: consumption_id,
            execution_allowed: enforcement.execution_allowed,
            execution_attempted: attempted,
            effect_applied,
            effect_digest: side_effect.as_ref().map(|r| r.effect_digest.clone()),
            failure_reason,
            core_state: enforcement.state,
            sequence: enforcement.sequence,
            timestamp: now,
        };
        GoldenPathResult {
            outcome: if effect_applied {
                GoldenPathOutcome::Executed
            } else if attempted {
                GoldenPathOutcome::Attempted
            } else {
                GoldenPathOutcome::Blocked
            },
            binding_valid,
            replay_free,
            not_expired,
            enforcement,
            receipt,
            side_effect,
        }
    }

    /// Evaluates without reserving a nonce, mutating the production registry,
    /// or constructing an execution authorization.
    pub fn shadow(
        &mut self,
        permit: &PermitCommit,
        envelope: &ActionEnvelope,
        clearance: &SignedClearanceEnvelope,
        now: u64,
    ) -> ShadowReceipt {
        let digest = envelope.digest();
        let binding_valid = clearance.binding_valid(&digest, self.effector.effector_id(), now)
            && permit.action_id == envelope.envelope_id
            && permit.connector_id == self.effector.effector_id();
        let not_expired = envelope.valid_until_epoch_ms > now;
        let replay_free = self
            .registry
            .records()
            .map(|records| {
                !records
                    .iter()
                    .any(|r| r.replay_nonce == envelope.replay_nonce)
            })
            .unwrap_or(false);
        let would_execute =
            binding_valid && not_expired && replay_free && clearance.clearance == Clearance::Clear;
        ShadowReceipt {
            execution_allowed: would_execute,
            would_execute,
            effect_applied: false,
            shadow_mode: true,
            reason: if would_execute {
                "core_would_allow".into()
            } else {
                "blocked".into()
            },
            permit_id: permit.permit_id.clone(),
            action_digest: digest,
            binding_valid,
            replay_free,
            not_expired,
            observed_at: now,
        }
    }
}

pub fn digest_hex(bytes: &[u8]) -> String {
    let digest = Sha256::digest(bytes);
    let hex: String = digest.iter().map(|byte| format!("{byte:02x}")).collect();
    format!("sha256:{hex}")
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{Arc, Barrier};
    use std::thread;
    use std::time::{SystemTime, UNIX_EPOCH};

    struct RecordingEffector {
        fail: bool,
    }
    impl ExclusiveEffector for RecordingEffector {
        fn effector_id(&self) -> &str {
            "connector.erp"
        }
        fn execute(
            &mut self,
            envelope: &ActionEnvelope,
            _: &ExecutionAuthorization,
        ) -> Result<SideEffectRecord, EffectorError> {
            if self.fail {
                return Err(EffectorError("synthetic failure".into()));
            }
            Ok(SideEffectRecord {
                effector_id: self.effector_id().into(),
                effect_id: "effect-1".into(),
                effect_digest: digest_hex(envelope.envelope_id.as_bytes()),
            })
        }
    }
    fn path(name: &str, fail: bool) -> (GoldenExecutionPath<RecordingEffector>, PathBuf) {
        let path = std::env::temp_dir().join(format!(
            "golden-{name}-{}.jsonl",
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let registry = DurablePermitConsumptionRegistry::open(&path).unwrap();
        (
            GoldenExecutionPath::new(RecordingEffector { fail }, registry),
            path,
        )
    }
    fn fixtures() -> (PermitCommit, ActionEnvelope, SignedClearanceEnvelope) {
        let envelope = ActionEnvelope {
            envelope_id: "act-1".into(),
            purpose_digest: "p".into(),
            authority_digest: "a".into(),
            target_digest: "t".into(),
            payload_digest: "d".into(),
            replay_nonce: "nonce-1".into(),
            valid_until_epoch_ms: 2000,
        };
        let mut clearance = SignedClearanceEnvelope {
            clearance_id: "clr-1".into(),
            clearance: Clearance::Clear,
            action_envelope_digest: envelope.digest(),
            effector_id: "connector.erp".into(),
            issued_at_epoch_ms: 1000,
            valid_until_epoch_ms: 2000,
            binding_digest: String::new(),
        };
        clearance.binding_digest = clearance.expected_binding_digest();
        (
            PermitCommit {
                permit_id: "permit-1".into(),
                execution_id: "exec-1".into(),
                action_id: "act-1".into(),
                connector_id: "connector.erp".into(),
                capability: "write".into(),
                idempotency_key: "idem-1".into(),
                reservation_id: "res-1".into(),
            },
            envelope,
            clearance,
        )
    }

    #[test]
    fn restart_replay_is_blocked() {
        let (mut first, path) = path("restart", false);
        let (permit, envelope, clearance) = fixtures();
        assert!(
            first
                .process(&permit, &envelope, &clearance, 1500)
                .receipt
                .effect_applied
        );
        drop(first);
        let registry = DurablePermitConsumptionRegistry::open(&path).unwrap();
        let mut restarted = GoldenExecutionPath::new(RecordingEffector { fail: false }, registry);
        let replay = restarted.process(&permit, &envelope, &clearance, 1501);
        assert!(!replay.receipt.execution_allowed);
        assert!(!replay.receipt.effect_applied);
        std::fs::remove_file(path).unwrap();
    }

    #[test]
    fn failed_effector_still_consumes_nonce_and_receipts_attempt() {
        let (mut path, file) = path("failure", true);
        let (permit, envelope, clearance) = fixtures();
        let result = path.process(&permit, &envelope, &clearance, 1500);
        assert!(result.receipt.execution_attempted);
        assert!(!result.receipt.effect_applied);
        assert!(!result.receipt.consumption_record_id.is_empty());
        let replay = path.process(&permit, &envelope, &clearance, 1501);
        assert!(!replay.receipt.execution_allowed);
        std::fs::remove_file(file).unwrap();
    }

    #[test]
    fn corrupt_registry_is_rejected() {
        let (_, file) = path("corrupt", false);
        std::fs::write(&file, b"not-json\n").unwrap();
        assert!(matches!(
            DurablePermitConsumptionRegistry::open(&file),
            Err(RegistryError::Corrupt)
        ));
        std::fs::remove_file(file).unwrap();
    }

    #[test]
    fn unavailable_registry_fails_closed() {
        let directory = std::env::temp_dir();
        assert!(matches!(
            DurablePermitConsumptionRegistry::open(directory),
            Err(RegistryError::Unavailable)
        ));
    }

    #[test]
    fn parallel_double_consume_has_one_winner() {
        let (_, file) = path("parallel", false);
        let registry = Arc::new(DurablePermitConsumptionRegistry::open(&file).unwrap());
        let barrier = Arc::new(Barrier::new(2));
        let mut handles = Vec::new();
        for _ in 0..2 {
            let registry = Arc::clone(&registry);
            let barrier = Arc::clone(&barrier);
            handles.push(thread::spawn(move || {
                let (permit, envelope, clearance) = fixtures();
                barrier.wait();
                registry.reserve_and_consume(&permit, &envelope, &clearance, "connector.erp", 1500)
            }));
        }
        let successes = handles
            .into_iter()
            .map(|handle| handle.join().unwrap())
            .filter(Result::is_ok)
            .count();
        assert_eq!(successes, 1);
        std::fs::remove_file(file).unwrap();
    }

    #[test]
    fn shadow_never_executes_or_consumes() {
        struct PanicEffector;
        impl ExclusiveEffector for PanicEffector {
            fn effector_id(&self) -> &str {
                "connector.erp"
            }
            fn execute(
                &mut self,
                _: &ActionEnvelope,
                _: &ExecutionAuthorization,
            ) -> Result<SideEffectRecord, EffectorError> {
                panic!("shadow called effector")
            }
        }
        let (_, file) = path("shadow", false);
        let registry = DurablePermitConsumptionRegistry::open(&file).unwrap();
        let mut path = GoldenExecutionPath::new(PanicEffector, registry);
        let (permit, envelope, clearance) = fixtures();
        let receipt = path.shadow(&permit, &envelope, &clearance, 1500);
        assert!(receipt.would_execute);
        assert!(!receipt.effect_applied);
        assert!(path.registry.records().unwrap().is_empty());
        std::fs::remove_file(file).unwrap();
    }

    #[test]
    fn halt_is_sticky_at_the_execution_boundary() {
        // Once the core halts, a perfectly valid permit is still refused with
        // no side effect — the fail-closed state is enforced at the boundary,
        // not just in the isolated core.
        let (mut path, file) = path("sticky-halt", false);
        let (permit, envelope, clearance) = fixtures();

        let mut denied = clearance.clone();
        denied.clearance = Clearance::Denied;
        let first = path.process(&permit, &envelope, &denied, 1500);
        assert!(!first.receipt.execution_allowed);
        assert!(!first.receipt.effect_applied);
        assert_eq!(path.core_state(), CoreState::Halt);

        let second = path.process(&permit, &envelope, &clearance, 1500);
        assert!(!second.receipt.execution_allowed);
        assert!(!second.receipt.execution_attempted);
        assert!(!second.receipt.effect_applied);
        assert_eq!(path.core_state(), CoreState::Halt);
        std::fs::remove_file(file).unwrap();
    }

    #[test]
    fn uncertain_collapses_to_halt_without_side_effect() {
        // The boundary only accepts Clear clearances; an Uncertain verdict is
        // fail-closed to Halt (no intermediate state at the commit boundary).
        let (mut path, file) = path("uncertain-halt", false);
        let (permit, envelope, clearance) = fixtures();

        let mut uncertain = clearance.clone();
        uncertain.clearance = Clearance::Uncertain;
        let result = path.process(&permit, &envelope, &uncertain, 1500);
        assert!(!result.receipt.execution_allowed);
        assert!(!result.receipt.execution_attempted);
        assert!(!result.receipt.effect_applied);
        assert_eq!(path.core_state(), CoreState::Halt);
        std::fs::remove_file(file).unwrap();
    }

    #[test]
    fn integrity_failure_at_boundary_halts_later_valid_permits() {
        // A corrupt binding poisons the core for subsequent valid permits.
        let (mut path, file) = path("poisoned", false);
        let (permit, envelope, clearance) = fixtures();

        let mut corrupted = clearance.clone();
        corrupted.action_envelope_digest = "tampered".into();
        let first = path.process(&permit, &envelope, &corrupted, 1500);
        assert!(!first.receipt.execution_allowed);
        assert_eq!(path.core_state(), CoreState::Halt);

        let second = path.process(&permit, &envelope, &clearance, 1500);
        assert!(!second.receipt.execution_allowed);
        assert!(!second.receipt.execution_attempted);
        assert!(!second.receipt.effect_applied);
        std::fs::remove_file(file).unwrap();
    }

    // Token pinned from the Python governance chain (RFC 8785/jsoncanon) so the
    // Rust reset path is provably byte-identical across languages.
    const GOLDEN_RESET_TOKEN: &str = r#"{"token_type":"valo-reset-authorization","action":"RESET","decision_id":"dec-reset","target_id":"connector.erp","scheme":"threshold","required":2,"epoch":0,"operators":["op-1","op-2"],"approval_digest":"sha256:436249efe201f18844f629665adade8fd475c25b4544194a97c9d15b27d054ad","issued_at":"2026-08-06T12:00:00+00:00","token_digest":"sha256:3e456fe2efc4bc435b02b8782e11ed97d3916de9b79f074d0f92a9b388b5ee5c"}"#;

    // A token issued for a DIFFERENT target (engine-1) must be rejected here.
    const FOREIGN_RESET_TOKEN: &str = r#"{"token_type":"valo-reset-authorization","action":"RESET","decision_id":"dec-reset","target_id":"engine-1","scheme":"threshold","required":2,"epoch":0,"operators":["op-1","op-2"],"approval_digest":"sha256:436249efe201f18844f629665adade8fd475c25b4544194a97c9d15b27d054ad","issued_at":"2026-08-06T12:00:00+00:00","token_digest":"sha256:4386162a360baca26d863d5177f20fdfb1226e06b4bbcc6aaf3e7884f0cafb18"}"#;

    #[test]
    fn human_reset_through_verified_token_lifts_halt() {
        let (mut path, file) = path("reset-token", false);
        // Trigger a halt at the boundary.
        let (permit, envelope, clearance) = fixtures();
        let mut denied = clearance.clone();
        denied.clearance = Clearance::Denied;
        path.process(&permit, &envelope, &denied, 1500);
        assert_eq!(path.core_state(), CoreState::Halt);

        // A verified token bound to this effector lifts the halt.
        let reset = path.human_reset(GOLDEN_RESET_TOKEN);
        assert!(reset.is_ok());
        assert_eq!(path.core_state(), CoreState::Normal);

        std::fs::remove_file(file).unwrap();
    }

    #[test]
    fn human_reset_rejects_token_bound_to_other_effector() {
        let (mut path, file) = path("foreign-reset", false);
        let (permit, envelope, clearance) = fixtures();
        let mut denied = clearance.clone();
        denied.clearance = Clearance::Denied;
        path.process(&permit, &envelope, &denied, 1500);
        assert_eq!(path.core_state(), CoreState::Halt);

        let reset = path.human_reset(FOREIGN_RESET_TOKEN);
        assert!(matches!(reset, Err(ResetError::InvalidResetToken(_))));
        assert_eq!(path.core_state(), CoreState::Halt); // still halted
        std::fs::remove_file(file).unwrap();
    }
}
