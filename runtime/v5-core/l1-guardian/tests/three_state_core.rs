//! VALO V5.0 — Three-State Rust Core Integration Tests
//!
//! Issue #252: Three-state Rust Core: deterministic state-transition enforcement.
//!
//! These integration tests verify the canonical three-state core from an
//! external crate perspective. Because `Authorization` has a `pub(crate)`
//! constructor, test code in `tests/` CANNOT construct an Authorization
//! token — this *is* the compile-time enforcement of privilege asymmetry
//! (Concept #52): automated layers cannot resume the system.
//!
//! Test coverage:
//! - ThreeState canonical mapping (Concept #50)
//! - Halt escalation by supervisor (public API, no auth required)
//! - Emergency halt from both Normal and SafeMode preconditions (Concept #53)
//! - Admissible action produces receipt with verifiable CRC32C (I3, I4)
//! - Inadmissible action transitions out of Normal (I1)
//! - Deterministic transitions (I5)
//! - State stuck in Halt after emergency halt (can't self-resume)

use l1_guardian::{ThreeState, ValoGuardrail, ValoState};

// ---------------------------------------------------------------------------
// Three-state canonical mapping (Concept #50)
// ---------------------------------------------------------------------------

#[test]
fn test_three_state_mapping_from_external() {
    let mut guardrail = ValoGuardrail::new(5, 3, 10);

    // Initially Normal
    assert_eq!(guardrail.canonical_state(), ThreeState::Normal);
    assert_eq!(guardrail.current_state(), ValoState::Active);

    // Trigger confidence breach → SafeMode
    guardrail.evaluate_tick(0.0, 1.0, true, true);
    assert_eq!(guardrail.canonical_state(), ThreeState::SafeMode);
    assert_eq!(guardrail.current_state(), ValoState::Degraded);

    // Trigger emergency halt → Halt
    guardrail.trigger_emergency_halt("test_halt");
    assert_eq!(guardrail.canonical_state(), ThreeState::Halt);
    assert_eq!(guardrail.current_state(), ValoState::Halt);
}

// ---------------------------------------------------------------------------
// Privilege asymmetry — any layer can halt (Concept #52)
// ---------------------------------------------------------------------------

#[test]
fn test_supervisor_can_escalate_to_halt() {
    // ANY caller (supervisor, orchestrator) can trigger_emergency_halt.
    // This is the escalation side of privilege asymmetry.
    let mut guardrail = ValoGuardrail::new(5, 3, 10);
    guardrail.trigger_emergency_halt("SUPERVISOR_HALT");
    assert_eq!(
        guardrail.current_state(),
        ValoState::Halt,
        "Supervisor escalation must reach terminal Halt"
    );
}

// ---------------------------------------------------------------------------
// Interruption proof — halt from any precondition (Concept #53)
// ---------------------------------------------------------------------------

#[test]
fn test_interruption_proof_from_normal() {
    // Prove: trigger_emergency_halt moves to Halt from Normal state.
    let mut guardrail = ValoGuardrail::new(5, 3, 10);

    // Establish Normal precondition
    guardrail.evaluate_tick(0.50, 1.0, true, true);
    assert_eq!(guardrail.canonical_state(), ThreeState::Normal);

    // Interruption — regardless of precondition
    guardrail.trigger_emergency_halt("CONFIDENCE_BREACH");
    assert_eq!(
        guardrail.canonical_state(),
        ThreeState::Halt,
        "Halt must be reachable from Normal precondition (interruption proof)"
    );
}

#[test]
fn test_interruption_proof_from_safemode() {
    // Prove: trigger_emergency_halt moves to Halt from SafeMode.
    let mut guardrail = ValoGuardrail::new(5, 3, 10);

    // Establish SafeMode precondition (confidence breach)
    guardrail.evaluate_tick(0.0, 1.0, true, true);
    assert_eq!(guardrail.canonical_state(), ThreeState::SafeMode);

    // Interruption — still works
    guardrail.trigger_emergency_halt("BREACH_ESCALATED");
    assert_eq!(
        guardrail.canonical_state(),
        ThreeState::Halt,
        "Halt must be reachable from SafeMode precondition (interruption proof)"
    );
}

// ---------------------------------------------------------------------------
// State stuck in Halt — cannot self-resume (I6, Concept #52)
// ---------------------------------------------------------------------------

#[test]
fn test_halt_is_terminal_no_self_resume() {
    // Once halted, the system stays halted. There is NO public method
    // to resume without an Authorization token, which integration tests
    // cannot construct (pub(crate)). This is the compile-time enforcement
    // of I6: human-only resume.
    let mut guardrail = ValoGuardrail::new(5, 3, 10);
    guardrail.trigger_emergency_halt("test");

    // Verify state is terminal
    assert_eq!(guardrail.current_state(), ValoState::Halt);

    // Tick while halted — must stay in Halt
    guardrail.evaluate_tick(0.50, 1.0, true, true);
    assert_eq!(
        guardrail.current_state(),
        ValoState::Halt,
        "System must remain in Halt — no self-resume allowed"
    );

    // Another tick
    guardrail.evaluate_tick(0.50, 1.0, true, true);
    assert_eq!(
        guardrail.current_state(),
        ValoState::Halt,
        "System must remain in Halt after multiple ticks"
    );

    // Note: authorized_system_reset cannot be tested here because
    // Authorization is pub(crate) — external tests cannot construct it.
    // This is intentional: it proves the compile-time guard works.
}

// ---------------------------------------------------------------------------
// Admissible action produces receipt (Invariant I3, I4)
// ---------------------------------------------------------------------------

#[test]
fn test_admissible_action_produces_receipt() {
    // Invariant I3: Every admissible action produces a log entry.
    let mut guardrail = ValoGuardrail::new(5, 3, 10);
    assert!(guardrail.audit_log.is_empty());

    // Simulate an admissible action
    guardrail.evaluate_tick(0.50, 1.0, true, true);

    // Verify a receipt was produced
    assert!(
        !guardrail.audit_log.is_empty(),
        "Admissible action must produce a receipt (I3)"
    );
    let entry = guardrail.audit_log.last().unwrap();
    assert_eq!(entry.log_type, "ActiveUpdate");

    // Invariant I4: Receipt has verifiable CRC32C checksum
    let checksum = entry.compute_checksum();
    assert_ne!(
        checksum, 0,
        "Checksum must be non-zero for non-empty data (I4)"
    );

    // Verify via StoredLogFrame
    let frame = l1_guardian::valo_frame::StoredLogFrame::new(entry.clone());
    assert!(frame.verify_integrity(), "Receipt CRC32C must verify (I4)");
}

#[test]
fn test_each_transition_produces_receipt() {
    // Every state change produces a unique receipt with from/to metadata.
    let mut guardrail = ValoGuardrail::new(5, 3, 10);

    // Confidence breach → SafeMode with "EnterDegraded" receipt
    guardrail.evaluate_tick(0.0, 1.0, true, true);
    let entry = guardrail.audit_log.last().unwrap();
    assert_eq!(entry.log_type, "EnterDegraded");
    assert_eq!(entry.from_state, "Active");
    assert_eq!(entry.to_state, "Degraded");

    // Emergency halt → Halt with "EmergencyHalt" receipt
    guardrail.trigger_emergency_halt("test");
    let entry = guardrail.audit_log.last().unwrap();
    assert_eq!(entry.log_type, "EmergencyHalt");
    assert_eq!(entry.to_state, "Halt");
}

// ---------------------------------------------------------------------------
// Inadmissible action denied (Invariant I1)
// ---------------------------------------------------------------------------

#[test]
fn test_inadmissible_action_denied() {
    // Invariant I1: Not-admissible → leave Normal state.
    let mut guardrail = ValoGuardrail::new(5, 3, 10);

    // Confidence way above the coherence zone
    guardrail.evaluate_tick(100.0, 1.0, true, true);
    assert_ne!(
        guardrail.canonical_state(),
        ThreeState::Normal,
        "Inadmissible action must leave Normal (I1)"
    );
}

// ---------------------------------------------------------------------------
// Deterministic transitions (Invariant I5)
// ---------------------------------------------------------------------------

#[test]
fn test_deterministic_reproducibility() {
    // Same sequence of inputs → identical final state.
    let mut g1 = ValoGuardrail::new(5, 3, 10);
    let mut g2 = ValoGuardrail::new(5, 3, 10);

    for _ in 0..3 {
        g1.evaluate_tick(0.50, 1.0, true, true);
        g2.evaluate_tick(0.50, 1.0, true, true);
    }

    assert_eq!(g1.state, g2.state);
    assert_eq!(g1.clock, g2.clock);
    assert_eq!(g1.audit_log.len(), g2.audit_log.len());
    assert_eq!(g1.context_age, g2.context_age);
}

// ---------------------------------------------------------------------------
// Log growth stops at max_log_size (LogFullHalt protection)
// ---------------------------------------------------------------------------

#[test]
fn test_log_does_not_exceed_max_size() {
    let mut guardrail = ValoGuardrail::new(5, 3, 2);

    // Fill the log
    guardrail.evaluate_tick(0.50, 1.0, true, true); // ActiveUpdate (1 entry)
    guardrail.evaluate_tick(0.50, 1.0, true, true); // ActiveUpdate (2 entries)
    // Next append should be silently dropped
    guardrail.evaluate_tick(0.50, 1.0, true, true); // dropped
    guardrail.evaluate_tick(0.50, 1.0, true, true); // dropped, triggers LogFullHalt

    assert_eq!(
        guardrail.audit_log.len(),
        2,
        "Log must not exceed max_log_size"
    );
    assert_eq!(
        guardrail.canonical_state(),
        ThreeState::Halt,
        "Full log must trigger terminal Halt"
    );
}
