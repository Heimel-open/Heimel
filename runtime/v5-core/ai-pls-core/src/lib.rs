#![forbid(unsafe_code)]

/// External clearance result produced before the execution boundary.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Clearance {
    Clear = 0,
    Uncertain = 1,
    Denied = 2,
    Invalid = 3,
}

/// Canonical AI-PLS runtime state.
#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CoreState {
    Normal = 0,
    SafeMode = 1,
    Halt = 2,
}

/// Minimal, model-agnostic signal accepted by the enforcement core.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct ExecutionSignal {
    pub clearance: Clearance,
    pub envelope_integrity_valid: bool,
    pub receipt_valid: bool,
    pub context_valid: bool,
    pub not_expired: bool,
    pub replay_free: bool,
}

impl ExecutionSignal {
    pub const fn clear() -> Self {
        Self {
            clearance: Clearance::Clear,
            envelope_integrity_valid: true,
            receipt_valid: true,
            context_valid: true,
            not_expired: true,
            replay_free: true,
        }
    }

    pub const fn technical_integrity_valid(self) -> bool {
        self.envelope_integrity_valid
            && self.receipt_valid
            && self.context_valid
            && self.not_expired
            && self.replay_free
    }
}

/// Result emitted by the core for every evaluated signal.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EnforcementResult {
    pub previous_state: CoreState,
    pub state: CoreState,
    pub execution_allowed: bool,
    pub reason: EnforcementReason,
    pub sequence: u64,
}

#[repr(u8)]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum EnforcementReason {
    Cleared = 0,
    Uncertain = 1,
    Denied = 2,
    InvalidClearance = 3,
    IntegrityFailure = 4,
    AlreadyHalted = 5,
    EmergencyHalt = 6,
    HumanReset = 7,
}

/// Opaque reset capability. External callers cannot construct it.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct HumanResetAuthorization {
    _private: (),
}

/// Canonical token fields, in RFC 8785 (JCS) sorted-key order. This must match
/// the governance chain's reset-authorization token payload exactly.
const RESET_TOKEN_FIELDS: [&str; 10] = [
    "action",
    "approval_digest",
    "decision_id",
    "epoch",
    "issued_at",
    "operators",
    "required",
    "scheme",
    "target_id",
    "token_type",
];

impl HumanResetAuthorization {
    /// Verify a reset-authorization token and, if valid and bound to
    /// ``target_id``, produce the reset capability.
    ///
    /// The token is issued by the governance chain's human-oversight authority
    /// only after a decision reaches quorum (M-of-N / rotating keys). The
    /// canonical SHA-256 digest is recomputed locally — no shared secret needed
    /// for verification.
    pub fn from_verified_human_path(
        token_json: &str,
        target_id: &str,
    ) -> Result<Self, ResetError> {
        let token: serde_json::Value = serde_json::from_str(token_json)
            .map_err(|_| ResetError::InvalidResetToken("token is not valid JSON".into()))?;
        if token.get("token_type").and_then(|v| v.as_str())
            != Some("valo-reset-authorization")
        {
            return Err(ResetError::InvalidResetToken(
                "not a valo reset-authorization token".into(),
            ));
        }
        if token.get("action").and_then(|v| v.as_str()) != Some("RESET") {
            return Err(ResetError::InvalidResetToken(
                "token action is not RESET".into(),
            ));
        }
        if token.get("target_id").and_then(|v| v.as_str()) != Some(target_id) {
            return Err(ResetError::InvalidResetToken(
                "token is not bound to this engine".into(),
            ));
        }
        let declared = token.get("token_digest").and_then(|v| v.as_str());
        match declared {
            Some(value) if value.starts_with("sha256:") => {}
            _ => {
                return Err(ResetError::InvalidResetToken(
                    "token carries no sha256 digest".into(),
                ))
            }
        }
        let expected = canonical_token_digest(&token);
        if expected != declared.unwrap_or_default() {
            return Err(ResetError::InvalidResetToken(
                "token digest mismatch: tampered or invalid".into(),
            ));
        }
        Ok(Self { _private: () })
    }

    /// Construct from a pre-verified human path (tests / trusted gateway).
    #[cfg(test)]
    pub(crate) const fn from_test_path() -> Self {
        Self { _private: () }
    }
}

/// Canonical RFC 8785 digest over the token payload, matching ``sha256:<hex>``.
pub fn canonical_token_digest(token: &serde_json::Value) -> String {
    let mut parts = Vec::new();
    for key in RESET_TOKEN_FIELDS {
        if let Some(value) = token.get(key) {
            let key_json = serde_json::to_string(key).unwrap_or_default();
            let value_json = serde_json::to_string(value).unwrap_or_default();
            parts.push(format!("{key_json}:{value_json}"));
        }
    }
    let canonical = format!("{{{}}}", parts.join(","));
    use sha2::{Digest, Sha256};
    let mut hasher = Sha256::new();
    hasher.update(canonical.as_bytes());
    format!("sha256:{:x}", hasher.finalize())
}

/// Deterministic execution enforcement state machine.
///
/// It does not interpret policy, semantics, confidence or model output.
/// Those concerns must be resolved before this boundary.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct AiPlsCore {
    state: CoreState,
    sequence: u64,
}

impl Default for AiPlsCore {
    fn default() -> Self {
        Self::new()
    }
}

impl AiPlsCore {
    pub const fn new() -> Self {
        Self {
            state: CoreState::Normal,
            sequence: 0,
        }
    }

    pub const fn state(&self) -> CoreState {
        self.state
    }

    pub const fn sequence(&self) -> u64 {
        self.sequence
    }

    pub fn evaluate(&mut self, signal: ExecutionSignal) -> EnforcementResult {
        let previous_state = self.state;
        self.sequence = self.sequence.saturating_add(1);

        if self.state == CoreState::Halt {
            return EnforcementResult {
                previous_state,
                state: self.state,
                execution_allowed: false,
                reason: EnforcementReason::AlreadyHalted,
                sequence: self.sequence,
            };
        }

        if !signal.technical_integrity_valid() {
            self.state = CoreState::Halt;
            return EnforcementResult {
                previous_state,
                state: self.state,
                execution_allowed: false,
                reason: EnforcementReason::IntegrityFailure,
                sequence: self.sequence,
            };
        }

        let (state, execution_allowed, reason) = match signal.clearance {
            Clearance::Clear => (CoreState::Normal, true, EnforcementReason::Cleared),
            Clearance::Uncertain => (CoreState::SafeMode, false, EnforcementReason::Uncertain),
            Clearance::Denied => (CoreState::Halt, false, EnforcementReason::Denied),
            Clearance::Invalid => (CoreState::Halt, false, EnforcementReason::InvalidClearance),
        };

        self.state = state;

        EnforcementResult {
            previous_state,
            state,
            execution_allowed,
            reason,
            sequence: self.sequence,
        }
    }

    /// Any caller may force the system into Halt.
    pub fn emergency_halt(&mut self) -> EnforcementResult {
        let previous_state = self.state;
        self.sequence = self.sequence.saturating_add(1);
        self.state = CoreState::Halt;

        EnforcementResult {
            previous_state,
            state: self.state,
            execution_allowed: false,
            reason: EnforcementReason::EmergencyHalt,
            sequence: self.sequence,
        }
    }

    /// Only a verified human authorization path may resume from Halt.
    pub fn human_reset(
        &mut self,
        _authorization: HumanResetAuthorization,
    ) -> Result<EnforcementResult, ResetError> {
        if self.state != CoreState::Halt {
            return Err(ResetError::NotHalted);
        }

        let previous_state = self.state;
        self.sequence = self.sequence.saturating_add(1);
        self.state = CoreState::Normal;

        Ok(EnforcementResult {
            previous_state,
            state: self.state,
            execution_allowed: false,
            reason: EnforcementReason::HumanReset,
            sequence: self.sequence,
        })
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ResetError {
    NotHalted,
    InvalidResetToken(&'static str),
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn clear_signal_allows_execution() {
        let mut core = AiPlsCore::new();
        let result = core.evaluate(ExecutionSignal::clear());

        assert_eq!(result.state, CoreState::Normal);
        assert!(result.execution_allowed);
        assert_eq!(result.reason, EnforcementReason::Cleared);
    }

    #[test]
    fn uncertain_signal_enters_safe_mode_without_execution() {
        let mut core = AiPlsCore::new();
        let mut signal = ExecutionSignal::clear();
        signal.clearance = Clearance::Uncertain;

        let result = core.evaluate(signal);

        assert_eq!(result.state, CoreState::SafeMode);
        assert!(!result.execution_allowed);
    }

    #[test]
    fn denied_signal_halts() {
        let mut core = AiPlsCore::new();
        let mut signal = ExecutionSignal::clear();
        signal.clearance = Clearance::Denied;

        let result = core.evaluate(signal);

        assert_eq!(result.state, CoreState::Halt);
        assert!(!result.execution_allowed);
    }

    #[test]
    fn integrity_failure_halts_even_when_clear() {
        let mut core = AiPlsCore::new();
        let mut signal = ExecutionSignal::clear();
        signal.receipt_valid = false;

        let result = core.evaluate(signal);

        assert_eq!(result.state, CoreState::Halt);
        assert_eq!(result.reason, EnforcementReason::IntegrityFailure);
    }

    #[test]
    fn halt_is_sticky_until_human_reset() {
        let mut core = AiPlsCore::new();
        core.emergency_halt();

        let result = core.evaluate(ExecutionSignal::clear());
        assert_eq!(result.state, CoreState::Halt);
        assert!(!result.execution_allowed);

        let reset = core
            .human_reset(HumanResetAuthorization::from_test_path())
            .expect("human reset should succeed");
        assert_eq!(reset.state, CoreState::Normal);
    }

    #[test]
    fn reset_is_rejected_before_halt() {
        let mut core = AiPlsCore::new();
        assert!(core
            .human_reset(HumanResetAuthorization::from_test_path())
            .is_err());
    }

    #[test]
    fn same_inputs_produce_same_transitions() {
        let signals = [
            ExecutionSignal::clear(),
            ExecutionSignal {
                clearance: Clearance::Uncertain,
                ..ExecutionSignal::clear()
            },
            ExecutionSignal {
                clearance: Clearance::Denied,
                ..ExecutionSignal::clear()
            },
        ];

        let mut a = AiPlsCore::new();
        let mut b = AiPlsCore::new();

        for signal in signals {
            assert_eq!(a.evaluate(signal), b.evaluate(signal));
        }
    }

    // Golden token pinned from the Python governance chain (RFC 8785/jsoncanon),
    // proving the Rust canonicalization is byte-identical across languages.
    const GOLDEN_TOKEN: &str = r#"{"token_type":"valo-reset-authorization","action":"RESET","decision_id":"dec-reset","target_id":"engine-1","scheme":"threshold","required":2,"epoch":0,"operators":["op-1","op-2"],"approval_digest":"sha256:436249efe201f18844f629665adade8fd475c25b4544194a97c9d15b27d054ad","issued_at":"2026-08-06T12:00:00+00:00","token_digest":"sha256:4386162a360baca26d863d5177f20fdfb1226e06b4bbcc6aaf3e7884f0cafb18"}"#;

    #[test]
    fn golden_token_verifies_cross_language() {
        let auth = HumanResetAuthorization::from_verified_human_path(GOLDEN_TOKEN, "engine-1")
            .expect("golden token must verify");
        let mut core = AiPlsCore::new();
        core.emergency_halt();
        assert!(core.human_reset(auth).is_ok());
    }

    #[test]
    fn reset_token_rejects_wrong_engine() {
        assert!(matches!(
            HumanResetAuthorization::from_verified_human_path(GOLDEN_TOKEN, "engine-2"),
            Err(ResetError::InvalidResetToken(_))
        ));
    }

    #[test]
    fn reset_token_rejects_tampered_digest() {
        let tampered = GOLDEN_TOKEN.replace(
            "sha256:4386162a360baca26d863d5177f20fdfb1226e06b4bbcc6aaf3e7884f0cafb18",
            "sha256:0000000000000000000000000000000000000000000000000000000000000000",
        );
        assert!(matches!(
            HumanResetAuthorization::from_verified_human_path(&tampered, "engine-1"),
            Err(ResetError::InvalidResetToken(_))
        ));
    }

    #[test]
    fn reset_token_rejects_wrong_action() {
        let tampered = GOLDEN_TOKEN.replace("\"action\":\"RESET\"", "\"action\":\"DELETE\"");
        assert!(matches!(
            HumanResetAuthorization::from_verified_human_path(&tampered, "engine-1"),
            Err(ResetError::InvalidResetToken(_))
        ));
    }
}
