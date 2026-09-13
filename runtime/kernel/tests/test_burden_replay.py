from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from valo_kernel.contracts.burden_replay import (
    ReplayOutcome,
    ReplayRequirement,
    RequirementStatus,
    assess_replay,
    seal_burden_record,
    seal_change_trigger,
    seal_replay_record,
)

NOW = datetime(2026, 8, 17, 13, 30, tzinfo=UTC)
STATE_A = "a" * 64
STATE_B = "b" * 64


def _pass_requirement(requirement_id: str = "req:evidence") -> ReplayRequirement:
    return ReplayRequirement(
        requirement_id=requirement_id,
        description="Required evidence is present",
        status=RequirementStatus.PASS,
        evidence_refs=("evidence:1",),
    )


def _replay(**overrides):
    values = {
        "replay_id": "replay:1",
        "tenant_id": "tenant:1",
        "subject_ref": "action:1",
        "version_ref": "contract:v1",
        "boundary_state_digest": STATE_A,
        "requirements": (_pass_requirement(),),
        "evidence_refs": ("evidence:1",),
        "created_at": NOW,
    }
    values.update(overrides)
    return seal_replay_record(**values)


def test_burden_record_binds_consequence_bearer_evidence_and_enforcement():
    burden = seal_burden_record(
        burden_id="burden:1",
        tenant_id="tenant:1",
        subject_ref="action:1",
        consequence_ref="consequence:cash-outflow",
        burden_type="financial",
        measurement_unit="EUR",
        measurement_period="per transaction",
        quantity=Decimal("125.50"),
        responsible_bearer_ref="principal:1",
        evidence_refs=("evidence:quote",),
        enforcement_ref="control:spend-cap",
        recorded_at=NOW,
    )

    assert burden.quantity == Decimal("125.50")
    assert burden.responsible_bearer_ref == "principal:1"
    assert burden.evidence_refs == ("evidence:quote",)
    assert burden.enforcement_ref == "control:spend-cap"
    assert burden.authority_effect == "NO_AUTHORITY_CREATION"
    assert burden.can_issue_clearance is False
    assert burden.can_execute is False


def test_burden_requires_point_or_complete_range_not_both():
    with pytest.raises(ValidationError):
        seal_burden_record(
            burden_id="burden:bad",
            tenant_id="tenant:1",
            subject_ref="action:1",
            consequence_ref="consequence:delay",
            burden_type="time",
            measurement_unit="hours",
            measurement_period="per action",
            responsible_bearer_ref="principal:1",
            evidence_refs=("evidence:1",),
            enforcement_ref="control:timeout",
            recorded_at=NOW,
        )

    ranged = seal_burden_record(
        burden_id="burden:range",
        tenant_id="tenant:1",
        subject_ref="action:1",
        consequence_ref="consequence:delay",
        burden_type="time",
        measurement_unit="hours",
        measurement_period="per action",
        lower_bound=Decimal(2),
        upper_bound=Decimal(4),
        responsible_bearer_ref="principal:1",
        evidence_refs=("evidence:1",),
        enforcement_ref="control:timeout",
        recorded_at=NOW,
    )
    assert ranged.lower_bound == Decimal(2)
    assert ranged.upper_bound == Decimal(4)


def test_replay_requirement_needs_evidence_for_pass_and_reason_for_non_pass():
    with pytest.raises(ValidationError):
        ReplayRequirement(
            requirement_id="req:bad-pass",
            description="No evidence",
            status=RequirementStatus.PASS,
        )

    with pytest.raises(ValidationError):
        ReplayRequirement(
            requirement_id="req:bad-fail",
            description="No reason",
            status=RequirementStatus.FAIL,
        )


def test_complete_replay_is_reconstructable_and_non_authorizing():
    replay = _replay(
        burden_refs=("burden:1",),
        assumption_refs=("assumption:1",),
        change_log_refs=("change:none",),
    )
    assessment = assess_replay(replay, evaluated_at=NOW + timedelta(seconds=1))

    assert assessment.outcome == ReplayOutcome.COMPLETE
    assert assessment.can_rely_on_replay is True
    assert assessment.blocking_requirement_ids == ()
    assert replay.can_issue_clearance is False
    assert replay.can_execute is False


def test_hard_failure_cannot_be_offset_by_other_passes():
    failed = ReplayRequirement(
        requirement_id="req:authority-state",
        description="Authority state must be fresh",
        status=RequirementStatus.FAIL,
        evidence_refs=("evidence:stale-state",),
        reason_codes=("STALE_STATE",),
    )
    replay = _replay(
        requirements=(_pass_requirement("req:policy"), failed),
        evidence_refs=("evidence:policy", "evidence:stale-state"),
    )

    assessment = assess_replay(replay, evaluated_at=NOW + timedelta(seconds=1))

    assert assessment.outcome == ReplayOutcome.INCOMPLETE
    assert assessment.can_rely_on_replay is False
    assert assessment.blocking_requirement_ids == ("req:authority-state",)
    assert "HARD_REQUIREMENT_NOT_PASS" in assessment.reason_codes


def test_soft_failure_does_not_override_hard_gate_result():
    soft = ReplayRequirement(
        requirement_id="req:advisory",
        description="Advisory preference",
        hard_requirement=False,
        status=RequirementStatus.HOLD,
        reason_codes=("ADVISORY_UNRESOLVED",),
    )
    replay = _replay(
        requirements=(_pass_requirement("req:hard"), soft),
        evidence_refs=("evidence:1",),
    )

    assessment = assess_replay(replay, evaluated_at=NOW + timedelta(seconds=1))
    assert assessment.outcome == ReplayOutcome.COMPLETE
    assert replay.failed_requirement_ids == ("req:advisory",)


def test_undeclared_replay_components_fail_completeness():
    replay = _replay(
        assumptions_declared=False,
        failures_declared=False,
        changes_declared=False,
    )

    assessment = assess_replay(replay, evaluated_at=NOW + timedelta(seconds=1))

    assert assessment.outcome == ReplayOutcome.INCOMPLETE
    assert set(assessment.reason_codes) == {
        "ASSUMPTIONS_UNDECLARED",
        "CHANGE_LOG_UNDECLARED",
        "FAILURE_LIST_UNDECLARED",
    }


def test_material_change_invalidates_prior_replay():
    replay = _replay()
    trigger = seal_change_trigger(
        trigger_id="change:1",
        tenant_id=replay.tenant_id,
        subject_ref=replay.subject_ref,
        prior_replay_digest=replay.replay_digest,
        prior_state_digest=STATE_A,
        new_state_digest=STATE_B,
        material=True,
        changed_refs=("state:authority",),
        affected_requirement_ids=("req:evidence",),
        evidence_refs=("evidence:state-change",),
        observed_at=NOW + timedelta(seconds=1),
    )

    assessment = assess_replay(
        replay,
        change_triggers=(trigger,),
        evaluated_at=NOW + timedelta(seconds=2),
    )

    assert assessment.outcome == ReplayOutcome.INVALIDATED
    assert assessment.invalidating_trigger_ids == ("change:1",)
    assert assessment.can_rely_on_replay is False


def test_non_material_change_does_not_invalidate_prior_replay():
    replay = _replay()
    trigger = seal_change_trigger(
        trigger_id="change:cosmetic",
        tenant_id=replay.tenant_id,
        subject_ref=replay.subject_ref,
        prior_replay_digest=replay.replay_digest,
        prior_state_digest=STATE_A,
        new_state_digest=STATE_B,
        material=False,
        changed_refs=("metadata:label",),
        evidence_refs=("evidence:label-change",),
        observed_at=NOW + timedelta(seconds=1),
    )

    assessment = assess_replay(
        replay,
        change_triggers=(trigger,),
        evaluated_at=NOW + timedelta(seconds=2),
    )
    assert assessment.outcome == ReplayOutcome.COMPLETE


def test_material_change_requires_affected_requirements_and_new_state():
    replay = _replay()

    with pytest.raises(ValidationError):
        seal_change_trigger(
            trigger_id="change:no-scope",
            tenant_id=replay.tenant_id,
            subject_ref=replay.subject_ref,
            prior_replay_digest=replay.replay_digest,
            prior_state_digest=STATE_A,
            new_state_digest=STATE_B,
            material=True,
            changed_refs=("state:x",),
            evidence_refs=("evidence:x",),
            observed_at=NOW,
        )

    with pytest.raises(ValidationError):
        seal_change_trigger(
            trigger_id="change:same-state",
            tenant_id=replay.tenant_id,
            subject_ref=replay.subject_ref,
            prior_replay_digest=replay.replay_digest,
            prior_state_digest=STATE_A,
            new_state_digest=STATE_A,
            material=False,
            changed_refs=("metadata:x",),
            evidence_refs=("evidence:x",),
            observed_at=NOW,
        )


def test_replay_digest_tampering_fails_closed():
    replay = _replay()
    payload = replay.model_dump(mode="python")
    payload["version_ref"] = "contract:tampered"

    with pytest.raises(ValidationError, match="replay digest mismatch"):
        type(replay)(**payload)
