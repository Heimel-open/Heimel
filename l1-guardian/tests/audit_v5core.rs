//! Audit test for valo-v5-core revalidation (commit 17f32f0).
//!
//! Reproduces the residual findings:
//! - confidence/syntax/latency checks still drive the state machine directly.
//! - Degraded maps to SafeMode with explicit receipt semantics.
//! - append_log stores plain LogEntry; StoredLogFrame wraps it when needed.
//! - audit_log is a public Vec<LogEntry>; entries can be mutated with no detection.
//! - Filling the log -> LogFullHalt with NO new log entry written.
//! - ValoGuardrail::new does not validate bounds (max_context_age=0 underflows).
//! - C0 multipliers from env are not validated at startup (NaN accepted).

use l1_guardian::valo_frame::LogEntry;
use l1_guardian::{ThreeState, ValoGuardrail, ValoState};
use std::panic::{catch_unwind, AssertUnwindSafe};

#[test]
fn step2_confidence_breach_moves_to_degraded() {
    let mut g = ValoGuardrail::new(5, 3, 10);
    // confidence below the zone drives the machine into Degraded
    g.evaluate_tick(0.50, 1.0, true, true);
    assert_eq!(g.current_state(), ValoState::Degraded);
    assert_eq!(g.canonical_state(), ThreeState::SafeMode);
    println!("[OBSERVED] evaluate_tick(confidence breach) -> Degraded/SafeMode");
}

#[test]
fn step3_degraded_maps_to_safe_mode() {
    let mut g = ValoGuardrail::new(5, 3, 10);
    g.evaluate_tick(100.0, 1.0, true, true); // forces Degraded
    assert_eq!(g.canonical_state(), ThreeState::SafeMode);
    println!("[OBSERVED] Degraded -> SafeMode; explicit state mapping preserved");
}

#[test]
fn step5_append_log_records_current_transition() {
    let mut g = ValoGuardrail::new(5, 3, 10);
    g.evaluate_tick(0.50, 1.0, true, true);
    // active log element is a plain LogEntry; the frame wrapper is separate
    let entry: &LogEntry = g.audit_log.last().unwrap();
    assert_eq!(entry.log_type, "EnterDegraded");
    println!("[OBSERVED] append_log pushes LogEntry directly; StoredLogFrame/CRC remains a wrapper");
}

#[test]
fn step6_audit_log_public_mutation_undetected() {
    let mut g = ValoGuardrail::new(5, 3, 10);
    g.evaluate_tick(0.50, 1.0, true, true);
    let len_before = g.audit_log.len();
    // mutate a logged entry directly (public field, no integrity re-check)
    if let Some(e) = g.audit_log.last_mut() {
        e.log_type = "TamperedEntry";
    }
    // no API detects the tamper; no checksum verification runs on read
    assert_eq!(g.audit_log.last().unwrap().log_type, "TamperedEntry");
    assert_eq!(g.audit_log.len(), len_before);
    println!("[OBSERVED] audit_log is public Vec<LogEntry>; tampered entry not auto-detected");
}

#[test]
fn step7_logfullhalt_writes_no_new_entry() {
    let mut g = ValoGuardrail::new(5, 3, 1); // max_log_size = 1
    g.evaluate_tick(0.50, 1.0, true, true); // adds 1 entry -> full
    let len_full = g.audit_log.len();
    assert_eq!(len_full, 1);
    g.evaluate_tick(0.50, 1.0, true, true); // should transition to LogFullHalt
    assert_eq!(g.current_state(), ValoState::LogFullHalt);
    // the LogFullHalt transition did NOT append a new entry
    assert_eq!(g.audit_log.len(), len_full);
    println!("[OBSERVED] LogFullHalt reached with NO new log entry (transition not receipted)");
}

#[test]
fn step9_unvalidated_bounds_underflow() {
    // ValoGuardrail::new does not validate max_context_age > 0.
    // evaluate_tick uses max_context_age - 1 -> usize underflow with 0.
    let mut g = ValoGuardrail::new(5, 0, 10); // max_context_age = 0
    let result = catch_unwind(AssertUnwindSafe(|| {
        g.evaluate_tick(0.50, 1.0, true, true);
    }));
    // Either it panics (debug underflow) or silently wraps — both show no startup validation.
    println!(
        "[OBSERVED] ValoGuardrail::new(5,0,10): max_context_age=0 not rejected; \
         evaluate_tick underflow behavior = {}",
        if result.is_ok() { "wrapped (no panic)" } else { "panicked (usize underflow)" }
    );
    // The key point: construction succeeded with invalid bounds (no validation).
    assert_eq!(g.max_context_age, 0);
}

#[test]
fn step10_c0_nan_accepted_at_startup() {
    // C0 multipliers are read from env and only .expect() on parse error.
    // "NaN" parses successfully as f64, so an invalid coherence multiplier is accepted.
    std::env::set_var("VALO_C0_LOW_MULTIPLIER", "NaN");
    std::env::set_var("VALO_C0_HIGH_MULTIPLIER", "-1");
    let mut g = ValoGuardrail::new(5, 3, 10);
    // startup did not reject NaN / negative C0; evaluation runs with them
    g.evaluate_tick(0.50, 1.0, true, true);
    println!(
        "[OBSERVED] VALO_C0_LOW_MULTIPLIER=NaN, HIGH=-1 accepted at startup (no range/NaN validation)"
    );
    std::env::remove_var("VALO_C0_LOW_MULTIPLIER");
    std::env::remove_var("VALO_C0_HIGH_MULTIPLIER");
}
