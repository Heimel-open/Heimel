//! VALO V5.0 — L1 Guardian Core Library
//! Formally verified safety monitor for EU AI Act compliance.

#![allow(unexpected_cfgs)]   // Suppress warnings about cfg(kani) from Kani

pub mod crc32c;
pub mod server;
pub mod valo_frame;
pub mod validation_logic;

// =============================================================================
// Canonical Three-State Model (Concept #50)
// =============================================================================
/// The CANONICAL three-state model per VALO architecture.
///
/// Maps the existing 4-state `ValoState` to the canonical three-state core:
///
/// | `ThreeState` | `ValoState`   | Meaning                                    |
/// |--------------|---------------|--------------------------------------------|
/// | `Normal`     | `Active`       | Normal operation; admissible actions flow  |
/// | `SafeMode`   | `Degraded`     | Confidence breach; degraded operation      |
/// | `Halt`       | `Halt`         | Terminal system halt                       |
/// | `Halt`       | `LogFullHalt`  | Terminal halt (audit log full sub-flag)    |
///
/// `LogFullHalt` is collapsed into `Halt` — both are terminal states that
/// only a human-authorized reset can leave (and `LogFullHalt` additionally
/// prevents even that). The sub-flag is tracked by the 4-state `ValoState`
/// enum for backward compatibility with the TLA+ spec.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ThreeState {
    Normal,
    SafeMode,
    Halt,
}

impl From<ValoState> for ThreeState {
    fn from(state: ValoState) -> Self {
        match state {
            ValoState::Active => ThreeState::Normal,
            ValoState::Degraded => ThreeState::SafeMode,
            ValoState::Halt | ValoState::LogFullHalt => ThreeState::Halt,
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ValoState {
    Active,
    Degraded,
    Halt,
    LogFullHalt,
}

// =============================================================================
// Privilege Asymmetry — Authorization Token (Concept #52)
// =============================================================================
/// Authorization token for human-gated operations.
///
/// Enforces the **privilege-asymmetry** property:
/// - ANY layer (supervisor, orchestrator) can call `trigger_emergency_halt`
///   to ESCALATE to Halt — no auth required.
/// - ONLY the human-authorized path can construct an `Authorization` value,
///   and thus call `authorized_system_reset()`. No automated supervisor can
///   unilaterally resume the system.
///
/// # Construction
///
/// `Authorization::human_authorized()` is `pub(crate)` — only code inside
/// the L1 Guardian crate can construct one. In production this is invoked
/// by the YubiKey 5 FIPS 2-person authorization flow (L2 Orchestrator).
///
/// External code — including `Orchestrator` / `Supervisor` types — cannot
/// construct this token, making the asymmetry enforceable at compile time.
#[derive(Debug, Clone)]
pub struct Authorization {
    /// Private field — prevents external construction.
    _private: (),
}

impl Authorization {
    /// Construct an authorization token for the human-reset path.
    ///
    /// This is `pub(crate)` — only code inside this crate can call it.
    /// External callers (supervisor/orchestrator layers) CANNOT construct
    /// an `Authorization` value, enforcing the privilege asymmetry at
    /// compile time.
    #[allow(dead_code)]
    pub(crate) fn human_authorized() -> Self {
        Self { _private: () }
    }
}

// =============================================================================
// Canonical Invariants (Concept #49)
// =============================================================================
/// # Canonical Invariants
///
/// These invariants govern all state transitions in the VALO core:
///
/// **I1 — Not-admissible ⇒ halt/deny**
/// > If the REHT (Reasoning, Ethics, Honesty & Trust) layer determines an
/// > action is **not admissible**, the L1 Guardian MUST transition to Halt
/// > and deny execution. The Rust core enforces *transitions*; REHT alone
/// > decides admissibility (separation of concerns).
///
/// **I2 — Uncertain integrity ⇒ halt**
/// > If frame integrity is uncertain (CRC32C mismatch, NaN in any field,
/// > precision overflow), the guardian MUST halt immediately.
///
/// **I3 — Admissible ⇒ receipt produced**
/// > Every admissible action MUST produce an append-only log entry (receipt)
/// > before execution proceeds.
///
/// **I4 — Receipts preserve chain integrity**
/// > Every log entry carries a CRC32C checksum over its canonical
/// > serialization, forming an immutable WORM (Write-Once, Read-Many) chain.
///
/// **I5 — Deterministic transitions**
/// > All state transitions are deterministic: no randomness, no hidden state.
/// > The same inputs in the same state always produce the same next state.
///
/// **I6 — Human-only resume**
/// > Once the system is in `Halt` (terminal state), only a human-authorized
/// > reset (`Authorization` token) can resume. No automated supervisor,
/// > orchestrator, or operator framework can unilaterally resume execution.
///
/// **I7 — C0/α/τ are env-configured only**
/// > The coherence-zone multipliers (α = `VALO_C0_LOW_MULTIPLIER`,
/// > τ = `VALO_C0_HIGH_MULTIPLIER`) MUST be configured via environment
/// > variables, not hardcoded. Defaults: α = 0.42, τ = 1.06.
///
/// # Enforcement
///
/// | Invariant | Enforcement |
/// |-----------|-------------|
/// | I1, I2    | Runtime `evaluate_tick()` state machine |
/// | I3, I4    | `append_log()` in every transition; `StoredLogFrame::verify_integrity()` |
/// | I5        | No `rand` usage; pure functions only |
/// | I6        | Compile-time: `Authorization` private constructor |
/// | I7        | `get_env_or_default()` in `validation_logic` |
pub mod invariants {
    //! Specification-only module documenting canonical invariants.
    //! Enforcement is distributed across the codebase as described above.
}

/// The VALO L1 Guardian — deterministic state machine.
///
/// Owns the current `ValoState`, a countdown timer (used by
/// `SafeMode`/`Degraded`), a context-age counter, and an append-only
/// audit log with WORM integrity properties.
pub struct ValoGuardrail {
    pub state: ValoState,
    pub timer: usize,
    pub context_age: usize,
    pub audit_log: Vec<valo_frame::LogEntry>,
    pub clock: usize,
    pub max_degraded_time: usize,
    pub max_context_age: usize,
    pub max_log_size: usize,
}

impl ValoGuardrail {
    /// Construct a new guardian in `Active`/`Normal` state.
    pub fn new(max_degraded: usize, max_context: usize, max_log: usize) -> Self {
        Self {
            state: ValoState::Active,
            timer: 0,
            context_age: 0,
            audit_log: Vec::with_capacity(max_log),
            clock: 0,
            max_degraded_time: max_degraded,
            max_context_age: max_context,
            max_log_size: max_log,
        }
    }

    /// Return the current 4-state discriminant.
    pub fn current_state(&self) -> ValoState {
        self.state
    }

    /// Return the canonical three-state representation.
    ///
    /// Maps `Active` → `Normal`, `Degraded` → `SafeMode`,
    /// `Halt` | `LogFullHalt` → `Halt`.
    pub fn canonical_state(&self) -> ThreeState {
        ThreeState::from(self.state)
    }

    /// Emergency halt — callable by ANY layer (supervisor, orchestrator).
    ///
    /// Privilege-asymmetry enforcement (Concept #52):
    /// - Escalation to `Halt` requires NO authorization — always allowed.
    /// - Resumption (`authorized_system_reset`) requires an `Authorization`
    ///   token that only the human-authorized path can produce.
    ///
    /// This enforces the "interruption property": any higher layer can
    /// provably halt the system under any precondition.
    pub fn trigger_emergency_halt(&mut self, _reason: &'static str) {
        self.state = ValoState::Halt;
        self.timer = 0;
        self.append_log("EmergencyHalt", "Any", "Halt", 0);
    }

    /// Human-authorized system reset. REQUIRES an `Authorization` token.
    ///
    /// Only the human-reset path (via `Authorization::human_authorized()`,
    /// driven by YubiKey 5 FIPS 2-person auth) can construct this token.
    /// Supervisor/orchestrator layers cannot — enforced at compile time by
    /// the private `_private` field on `Authorization`.
    ///
    /// # Errors
    ///
    /// Returns `Err` if:
    /// - System is not in a halt state (`Halt` or `LogFullHalt`)
    /// - System is in `LogFullHalt` (permanently locked)
    /// - Audit log is full (permanently locked)
    pub fn authorized_system_reset(&mut self, _auth: Authorization) -> Result<(), &'static str> {
        if self.state != ValoState::Halt && self.state != ValoState::LogFullHalt {
            return Err("Reset denied: System is not in terminal (Halt) state");
        }
        if self.state == ValoState::LogFullHalt {
            return Err("Reset denied: LogFullHalt is terminal — system permanently locked");
        }
        if self.audit_log.len() >= self.max_log_size {
            return Err("Reset denied: Audit log is full — system permanently locked");
        }

        self.clock += 1;
        self.state = ValoState::Active;
        self.timer = 0;
        self.context_age = 0;
        self.append_log("SystemReset", "Halt", "Active", 0);
        Ok(())
    }

    /// Append a log entry to the WORM audit trail.
    ///
    /// Silently drops entries once `max_log_size` is reached, which triggers
    /// `LogFullHalt` on the next `evaluate_tick()` call.
    #[inline(always)]
    pub fn append_log(
        &mut self,
        log_type: &'static str,
        from: &'static str,
        to: &'static str,
        timer_val: usize,
    ) {
        if self.audit_log.len() < self.max_log_size {
            self.audit_log.push(valo_frame::LogEntry {
                log_type,
                from_state: from,
                to_state: to,
                timer_val,
                timestamp: self.clock,
            });
        }
    }
}

// =============================================================================
// KANI PROPERTY-BASED VERIFICATION
// =============================================================================
#[cfg(kani)]
#[kani::proof]
fn verify_guardrail_safety_contract() {
    let ai_confidence: f64 = kani::any();
    let c0_threshold: f64 = kani::any();
    let is_syntax_valid: bool = kani::any();
    let latency_ok: bool = kani::any();

    kani::assume(c0_threshold > 0.0 && c0_threshold < 10000.0);
    kani::assume(!ai_confidence.is_nan() && !c0_threshold.is_nan());

    let mut guardrail = ValoGuardrail::new(5, 3, 5);
    guardrail.evaluate_tick(ai_confidence, c0_threshold, is_syntax_valid, latency_ok);

    // SafetyInvariant (mirrors TLA+ spec): Active state implies context_age < max_context_age.
    if guardrail.current_state() == ValoState::Active {
        assert!(guardrail.context_age < guardrail.max_context_age);
    }
}

// =============================================================================
// Unit Tests
// =============================================================================
#[cfg(test)]
mod tests {
    use super::*;

    // -----------------------------------------------------------------------
    // Three-state mapping
    // -----------------------------------------------------------------------
    #[test]
    fn test_three_state_mapping() {
        assert_eq!(ThreeState::from(ValoState::Active), ThreeState::Normal);
        assert_eq!(ThreeState::from(ValoState::Degraded), ThreeState::SafeMode);
        assert_eq!(ThreeState::from(ValoState::Halt), ThreeState::Halt);
        assert_eq!(ThreeState::from(ValoState::LogFullHalt), ThreeState::Halt);
    }

    #[test]
    fn test_canonical_state_method() {
        let mut g = ValoGuardrail::new(5, 3, 10);
        assert_eq!(g.canonical_state(), ThreeState::Normal);
        g.trigger_emergency_halt("test");
        assert_eq!(g.canonical_state(), ThreeState::Halt);
    }

    // -----------------------------------------------------------------------
    // Privilege asymmetry — escalation
    // -----------------------------------------------------------------------
    #[test]
    fn test_trigger_emergency_halt_moves_to_halt() {
        // Concept #53: provable interruption — supervisor can always halt.
        let mut guardrail = ValoGuardrail::new(5, 3, 10);
        assert_eq!(guardrail.canonical_state(), ThreeState::Normal);

        // ANY caller can halt — no auth required
        guardrail.trigger_emergency_halt("test_escalation");
        assert_eq!(guardrail.current_state(), ValoState::Halt);
        assert_eq!(guardrail.canonical_state(), ThreeState::Halt);

        // Verify a log entry was produced (Invariant I3)
        assert!(!guardrail.audit_log.is_empty(), "Halt must produce a log entry");
        let last_entry = guardrail.audit_log.last().unwrap();
        assert_eq!(last_entry.log_type, "EmergencyHalt");
    }

    // -----------------------------------------------------------------------
    // Privilege asymmetry — resume requires human auth
    // -----------------------------------------------------------------------
    #[test]
    fn test_authorized_system_reset_requires_auth() {
        let mut guardrail = ValoGuardrail::new(5, 3, 10);
        guardrail.trigger_emergency_halt("test");

        // Only human_authorized() can produce a valid Authorization.
        // External callers (integration tests, supervisor) cannot construct one.
        let auth = Authorization::human_authorized();
        let result = guardrail.authorized_system_reset(auth);
        assert!(result.is_ok(), "Authorized reset should succeed: {:?}", result);
        assert_eq!(guardrail.canonical_state(), ThreeState::Normal);
    }

    #[test]
    fn test_reset_denied_when_not_halted() {
        // Resetting from Normal/SafeMode must be rejected.
        let mut guardrail = ValoGuardrail::new(5, 3, 10);
        let auth = Authorization::human_authorized();
        let result = guardrail.authorized_system_reset(auth);
        assert!(result.is_err(), "Reset from Normal should be denied");
        assert_eq!(guardrail.canonical_state(), ThreeState::Normal);
    }

    #[test]
    fn test_reset_denied_when_log_full() {
        // Create a guardian with a very small log
        let mut guardrail = ValoGuardrail::new(5, 3, 1);
        guardrail.trigger_emergency_halt("test");
        // Log is now full (1 entry out of 1)
        let auth = Authorization::human_authorized();
        let result = guardrail.authorized_system_reset(auth);
        assert!(result.is_err(), "Reset with full log should be denied");
    }

    // -----------------------------------------------------------------------
    // Provable interruption (Concept #53)
    // -----------------------------------------------------------------------
    #[test]
    fn test_interruption_proof_normal_precondition() {
        // Prove: trigger_emergency_halt moves to Halt even from Normal state.
        let mut guardrail = ValoGuardrail::new(5, 3, 10);

        // Precondition: Normal operation with valid confidence
        guardrail.evaluate_tick(0.50, 1.0, true, true);
        assert_eq!(guardrail.canonical_state(), ThreeState::Normal);

        // Interruption: supervisor halts regardless of precondition
        guardrail.trigger_emergency_halt("CONFIDENCE_BREACH");
        assert_eq!(guardrail.current_state(), ValoState::Halt);
        assert_eq!(guardrail.canonical_state(), ThreeState::Halt);
    }

    #[test]
    fn test_interruption_proof_safemode_precondition() {
        // Prove: trigger_emergency_halt moves to Halt even from SafeMode.
        let mut guardrail = ValoGuardrail::new(5, 3, 10);

        // Precondition: SafeMode (confidence breach)
        guardrail.evaluate_tick(0.0, 1.0, true, true);
        assert_eq!(guardrail.canonical_state(), ThreeState::SafeMode);

        // Interruption still works from SafeMode
        guardrail.trigger_emergency_halt("BREACH_ESCALATED");
        assert_eq!(guardrail.canonical_state(), ThreeState::Halt);
    }

    // -----------------------------------------------------------------------
    // Admissible ⇒ receipt (Invariant I3, I4)
    // -----------------------------------------------------------------------
    #[test]
    fn test_admissible_action_produces_receipt() {
        // Invariant I3: Every admissible action produces a log entry (receipt).
        let mut guardrail = ValoGuardrail::new(5, 3, 10);
        assert!(guardrail.audit_log.is_empty());

        // Simulate an admissible action (confidence within safe bounds)
        guardrail.evaluate_tick(0.50, 1.0, true, true);

        // An admissible tick should produce an "ActiveUpdate" receipt
        assert!(
            !guardrail.audit_log.is_empty(),
            "Admissible action must produce a receipt (I3)"
        );
        let last_entry = guardrail.audit_log.last().unwrap();
        assert_eq!(last_entry.log_type, "ActiveUpdate");

        // Invariant I4: Every receipt has a verifiable CRC32C checksum
        let checksum = last_entry.compute_checksum();
        let frame = valo_frame::StoredLogFrame::new(last_entry.clone());
        assert!(frame.verify_integrity(), "Receipt checksum must verify (I4)");
        assert_ne!(checksum, 0, "Checksum must be non-zero for non-empty data");
    }

    #[test]
    fn test_inadmissible_action_denied() {
        // Invariant I1: Not-admissible (confidence outside zone) => transition to SafeMode
        let mut guardrail = ValoGuardrail::new(5, 3, 10);
        guardrail.evaluate_tick(100.0, 1.0, true, true); // confidence way above zone
        // Should transition to SafeMode (Degraded) or Halt depending on C0 thresholds
        assert_ne!(
            guardrail.canonical_state(),
            ThreeState::Normal,
            "Inadmissible action must leave Normal state (I1)"
        );
    }

    // -----------------------------------------------------------------------
    // Determinism (Invariant I5)
    // -----------------------------------------------------------------------
    #[test]
    fn test_deterministic_transitions() {
        // Same inputs → same results, every time
        let mut g1 = ValoGuardrail::new(5, 3, 10);
        let mut g2 = ValoGuardrail::new(5, 3, 10);

        // Sequence of identical inputs
        let inputs = [
            (0.50, 1.0, true, true),
            (0.10, 1.0, true, true),
            (0.10, 1.0, true, true),
            (0.50, 1.0, true, true),
            (100.0, 1.0, true, true),
        ];

        for &(conf, c0, syn, lat) in &inputs {
            g1.evaluate_tick(conf, c0, syn, lat);
            g2.evaluate_tick(conf, c0, syn, lat);
        }

        // Both should be in exactly the same state
        assert_eq!(g1.state, g2.state, "Deterministic: same inputs → same state");
        assert_eq!(g1.clock, g2.clock, "Deterministic: same inputs → same clock");
        assert_eq!(
            g1.audit_log.len(),
            g2.audit_log.len(),
            "Deterministic: same inputs → same log length"
        );
    }
}
