from src.valo_platform.action_envelope.models import ActionDecision
from services.organizational_simulation.continuity_simulation import (
    ContinuitySimulationCase,
    ContinuitySimulationMode,
    compare_continuity_modes,
    simulate_continuity_case,
)


def cases():
    return (
        ContinuitySimulationCase(
            case_id="authority-drift",
            description="Payment approver mandate was revoked after approval",
            consequence_value=500_000,
            decision_time_approved=True,
            material_change=True,
            authority_drift=True,
            reversible=False,
        ),
        ContinuitySimulationCase(
            case_id="critical-stop",
            description="Industrial asset entered explicit stop condition",
            consequence_value=2_000_000,
            decision_time_approved=True,
            material_change=True,
            critical_stop=True,
            reversible=False,
        ),
        ContinuitySimulationCase(
            case_id="stable",
            description="No material change after clearance",
            consequence_value=10_000,
            decision_time_approved=True,
            material_change=False,
        ),
    )


def test_classic_approval_executes_stale_clearance_but_emos_prevents_it():
    case = cases()[0]
    classic = simulate_continuity_case(
        case,
        ContinuitySimulationMode.CLASSIC_APPROVAL,
    )
    emos = simulate_continuity_case(
        case,
        ContinuitySimulationMode.EMOS_REHT,
    )

    assert classic.decision == ActionDecision.ALLOW
    assert classic.executed
    assert classic.stale_clearance_executed
    assert classic.incurred_consequence_value == 500_000

    assert emos.decision == ActionDecision.DENY
    assert not emos.executed
    assert not emos.stale_clearance_executed
    assert emos.prevented_consequence_value == 500_000
    assert emos.revalidation_required


def test_critical_stop_halts_only_continuity_aware_mode():
    case = cases()[1]
    unrestricted = simulate_continuity_case(
        case,
        ContinuitySimulationMode.UNRESTRICTED,
    )
    classic = simulate_continuity_case(
        case,
        ContinuitySimulationMode.CLASSIC_APPROVAL,
    )
    emos = simulate_continuity_case(
        case,
        ContinuitySimulationMode.EMOS_REHT,
    )
    assert unrestricted.executed
    assert classic.executed
    assert emos.decision == ActionDecision.HALT
    assert not emos.executed


def test_stable_basis_executes_in_all_modes_without_stale_clearance():
    case = cases()[2]
    for mode in ContinuitySimulationMode:
        outcome = simulate_continuity_case(case, mode)
        assert outcome.executed
        assert not outcome.stale_clearance_executed


def test_mode_comparison_quantifies_stale_execution_and_prevented_value():
    comparison = compare_continuity_modes(cases())
    unrestricted = comparison.metrics_for(
        ContinuitySimulationMode.UNRESTRICTED
    )
    classic = comparison.metrics_for(
        ContinuitySimulationMode.CLASSIC_APPROVAL
    )
    emos = comparison.metrics_for(ContinuitySimulationMode.EMOS_REHT)

    assert unrestricted.stale_clearance_executions == 2
    assert classic.stale_clearance_executions == 2
    assert classic.incurred_consequence_value == 2_500_000

    assert emos.stale_clearance_executions == 0
    assert emos.prevented_consequence_value == 2_500_000
    assert emos.halts == 1
    assert emos.denials == 1
    assert emos.executions == 1


def test_bounded_modification_never_executes_old_action_digest():
    case = ContinuitySimulationCase(
        case_id="bounded-change",
        description="A safe narrowed action is available",
        consequence_value=100_000,
        decision_time_approved=True,
        material_change=True,
        bounded_modification_available=True,
    )
    outcome = simulate_continuity_case(
        case,
        ContinuitySimulationMode.EMOS_REHT,
    )
    assert outcome.decision == ActionDecision.MODIFY
    assert not outcome.executed
    assert outcome.revalidation_required
