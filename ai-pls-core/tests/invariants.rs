use ai_pls_core::{AiPlsCore, Clearance, CoreState, EnforcementReason, ExecutionSignal};

#[test]
fn not_clear_never_executes() {
    for clearance in [Clearance::Uncertain, Clearance::Denied, Clearance::Invalid] {
        let mut core = AiPlsCore::new();
        let result = core.evaluate(ExecutionSignal {
            clearance,
            ..ExecutionSignal::clear()
        });
        assert!(!result.execution_allowed);
    }
}

#[test]
fn technical_invalidity_dominates_clearance() {
    let mut core = AiPlsCore::new();
    let result = core.evaluate(ExecutionSignal {
        receipt_valid: false,
        ..ExecutionSignal::clear()
    });

    assert_eq!(result.state, CoreState::Halt);
    assert_eq!(result.reason, EnforcementReason::IntegrityFailure);
}

#[test]
fn emergency_halt_reachable_from_normal_and_safe_mode() {
    let mut normal = AiPlsCore::new();
    assert_eq!(normal.emergency_halt().state, CoreState::Halt);

    let mut safe = AiPlsCore::new();
    safe.evaluate(ExecutionSignal {
        clearance: Clearance::Uncertain,
        ..ExecutionSignal::clear()
    });
    assert_eq!(safe.emergency_halt().state, CoreState::Halt);
}

#[test]
fn halt_remains_sticky_for_external_callers() {
    let mut core = AiPlsCore::new();
    core.emergency_halt();

    let result = core.evaluate(ExecutionSignal::clear());
    assert_eq!(result.state, CoreState::Halt);
    assert!(!result.execution_allowed);
    assert_eq!(result.reason, EnforcementReason::AlreadyHalted);
}
