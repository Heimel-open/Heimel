from datetime import datetime, timedelta, timezone

from src.valo_platform.continuous_integrity import (
    IntegrityDecision,
    IntegrityProfile,
    IntegrityState,
    IntegrityTrigger,
    capture_baseline,
    emit_checkpoint_receipt,
    evaluate_integrity,
    verify_checkpoint_chain,
)

NOW = datetime(2026, 7, 27, 3, 0, tzinfo=timezone.utc)
PROFILE = IntegrityProfile(
    profile_id="high-risk",
    weights={
        "authority": 0.2,
        "policy": 0.2,
        "objective": 0.15,
        "context": 0.05,
        "evidence": 0.15,
        "tools": 0.1,
        "model_harness": 0.05,
        "environment": 0.05,
        "risk": 0.05,
    },
    material_drift_threshold=0.2,
    baseline_validity_seconds=300,
)


def state(**changes) -> IntegrityState:
    data = dict(
        authority="a1",
        policy="p1",
        objective="o1",
        context="c1",
        evidence="e1",
        tools="t1",
        model_harness="m1",
        environment="env1",
        risk="r1",
        observed_at=NOW,
        valid_until=NOW + timedelta(minutes=10),
        critical_validity={
            "authority": True,
            "policy": True,
            "objective": True,
            "evidence": True,
            "tools": True,
            "environment": True,
        },
    )
    data.update(changes)
    return IntegrityState(**data)


def baseline():
    return capture_baseline(
        baseline_id="b1",
        case_id="case-1",
        action_ref="action-1",
        clearance_digest="sha256:" + "1" * 64,
        profile=PROFILE,
        state=state(),
        captured_at=NOW,
    )


def test_unchanged_fast_path_continues() -> None:
    result = evaluate_integrity(
        baseline=baseline(),
        current=state(),
        profile=PROFILE,
        trigger=IntegrityTrigger.CHECKPOINT,
        now=NOW + timedelta(seconds=1),
    )
    assert result.decision is IntegrityDecision.CONTINUE
    assert result.revalidation_required is False
    assert result.drift_score == 0.0


def test_material_policy_change_requires_reevaluation() -> None:
    result = evaluate_integrity(
        baseline=baseline(),
        current=state(policy="p2"),
        profile=PROFILE,
        trigger=IntegrityTrigger.POLICY_CHANGE,
        now=NOW + timedelta(seconds=2),
    )
    assert result.decision is IntegrityDecision.REEVALUATE
    assert result.revalidation_required is True
    assert "policy" in result.changed_fields


def test_critical_authority_failure_halts_independent_of_score() -> None:
    current = state(critical_validity={
        "authority": False,
        "policy": True,
        "objective": True,
        "evidence": True,
        "tools": True,
        "environment": True,
    })
    result = evaluate_integrity(
        baseline=baseline(),
        current=current,
        profile=PROFILE,
        trigger=IntegrityTrigger.AUTHORITY_CHANGE,
        now=NOW + timedelta(seconds=3),
    )
    assert result.decision is IntegrityDecision.HALT
    assert result.failed_invariants == ("authority",)


def test_irreversible_boundary_requires_reevaluation_without_drift() -> None:
    result = evaluate_integrity(
        baseline=baseline(),
        current=state(),
        profile=PROFILE,
        trigger=IntegrityTrigger.IRREVERSIBLE_BOUNDARY,
        now=NOW + timedelta(seconds=4),
    )
    assert result.decision is IntegrityDecision.REEVALUATE


def test_expired_baseline_requires_reevaluation() -> None:
    result = evaluate_integrity(
        baseline=baseline(),
        current=state(observed_at=NOW + timedelta(minutes=6)),
        profile=PROFILE,
        trigger=IntegrityTrigger.TIMEOUT,
        now=NOW + timedelta(minutes=6),
    )
    assert result.decision is IntegrityDecision.REEVALUATE


def test_expired_current_state_halts() -> None:
    result = evaluate_integrity(
        baseline=baseline(),
        current=state(valid_until=NOW + timedelta(seconds=1)),
        profile=PROFILE,
        trigger=IntegrityTrigger.CHECKPOINT,
        now=NOW + timedelta(seconds=2),
    )
    assert result.decision is IntegrityDecision.HALT
    assert "state_expired" in result.failed_invariants


def test_checkpoint_receipts_form_digest_chain() -> None:
    first = emit_checkpoint_receipt(
        receipt_id="r1",
        baseline=baseline(),
        current=state(),
        profile=PROFILE,
        trigger=IntegrityTrigger.CHECKPOINT,
        observed_at=NOW + timedelta(seconds=1),
    )
    second = emit_checkpoint_receipt(
        receipt_id="r2",
        baseline=baseline(),
        current=state(context="c2"),
        profile=PROFILE,
        trigger=IntegrityTrigger.TOOL_RESULT,
        previous_checkpoint_digest=first.digest(),
        observed_at=NOW + timedelta(seconds=2),
    )
    assert verify_checkpoint_chain((first, second))
    assert not verify_checkpoint_chain((second, first))
    assert first.grants_authority is False
    assert first.grants_clearance is False
