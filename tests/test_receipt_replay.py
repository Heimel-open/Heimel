from datetime import datetime, timedelta, timezone

import pytest

from src.valo_platform.action_envelope.models import ActionDecision
from src.valo_platform.decision_governance.continuity import (
    ContinuityBasisSnapshot,
    ContinuityClearanceState,
    ContinuityContractError,
    ContinuityDecision,
    ContinuityImpactAssessment,
    ContinuityMateriality,
    ContinuitySeverity,
    ContinuityTrigger,
    ContinuityTriggerKind,
    canonical_fingerprint_digest,
)
from src.valo_platform.operational_continuity.receipt_replay import (
    build_continuity_receipt_record,
    replay_continuity_receipt,
    verify_continuity_receipt_chain,
)


NOW = datetime(2026, 8, 1, 10, 30, tzinfo=timezone.utc)
CURRENT = {
    "authority": "sha256:authority",
    "policy": "sha256:policy",
    "context": "sha256:context",
    "state": "sha256:case",
    "evidence": "sha256:evidence",
}


def basis():
    return ContinuityBasisSnapshot(
        snapshot_id="basis-1",
        tenant_id="tenant-1",
        action_case_id="case-1",
        action_case_hash="sha256:case",
        clearance_ref="clearance-1",
        observed_at=NOW - timedelta(minutes=2),
        authority_fingerprint=CURRENT["authority"],
        policy_fingerprint=CURRENT["policy"],
        evidence_fingerprint=CURRENT["evidence"],
        context_fingerprint=CURRENT["context"],
        state_fingerprint=CURRENT["state"],
        purpose_binding_ref="purpose:1",
        valid_until=NOW + timedelta(hours=1),
    )


def trigger(trigger_id="trigger-1"):
    return ContinuityTrigger(
        trigger_id=trigger_id,
        tenant_id="tenant-1",
        action_case_id="case-1",
        action_case_hash="sha256:case",
        clearance_ref="clearance-1",
        trigger_kind=ContinuityTriggerKind.ENVIRONMENT_CHANGED,
        severity=ContinuitySeverity.LOW,
        source_ref="sensor:1",
        observer_ref="observer:1",
        observed_at=NOW - timedelta(seconds=10),
        previous_fingerprint="sha256:old",
        current_fingerprint="sha256:new",
        changed_fields=("wind",),
        source_evidence_refs=("sensor-event:1",),
        confidence=0.95,
        freshness=1.0,
        integrity_status="verified",
    )


def assessment(trigger_id="trigger-1"):
    return ContinuityImpactAssessment(
        assessment_id="assessment-1",
        tenant_id="tenant-1",
        trigger_refs=(trigger_id,),
        action_case_id="case-1",
        action_case_hash="sha256:case",
        clearance_ref="clearance-1",
        materiality=ContinuityMateriality.NO_MATERIAL_CHANGE,
        impact_dimensions=("environment",),
        reason_codes=("below_materiality_threshold",),
        evidence_refs=("sensor-event:1",),
        assessor_refs=("vaig:1",),
        confidence=0.96,
        assessed_at=NOW - timedelta(seconds=5),
    )


def decision(trigger_id="trigger-1"):
    current_basis = basis()
    return ContinuityDecision(
        continuity_decision_id="continuity-1",
        tenant_id="tenant-1",
        action_case_id="case-1",
        action_case_hash="sha256:case",
        clearance_ref="clearance-1",
        basis_snapshot_ref=current_basis.snapshot_id,
        basis_snapshot_digest=current_basis.snapshot_digest,
        trigger_refs=(trigger_id,),
        impact_assessment_refs=("assessment-1",),
        racs_outcome=ActionDecision.ALLOW,
        clearance_state_after=ContinuityClearanceState.ACTIVE,
        requires_new_action_case=False,
        requires_new_clearance=False,
        reason_codes=("decision_basis_continuity_preserved",),
        evidence_refs=("sensor-event:1", "assessment:assessment-1"),
        decider_ref="reht:continuity",
        decision_authority_ref="authority:reht",
        current_fingerprint_digest=canonical_fingerprint_digest(CURRENT),
        decided_at=NOW - timedelta(seconds=1),
        valid_until=NOW + timedelta(minutes=5),
    )


def receipt_snapshot(current_decision):
    return {
        "receipt_id": "receipt-1",
        "decision": "allow",
        "metadata": {
            "action_case_ref": "case-1",
            "action_case_hash": "sha256:case",
            "clearance_ref": "clearance-1",
            "continuity_basis_snapshot_ref": "basis-1",
            "continuity_trigger_refs": ["trigger-1"],
            "continuity_assessment_refs": ["assessment-1"],
            "continuity_decision_ref": "continuity-1",
            "continuity_decision_digest": current_decision.decision_digest,
        },
    }


def build(sequence=0, previous_chain_hash="0" * 64):
    current_decision = decision()
    return build_continuity_receipt_record(
        sequence=sequence,
        basis=basis(),
        triggers=(trigger(),),
        assessment=assessment(),
        decision=current_decision,
        recorded_at=NOW,
        previous_chain_hash=previous_chain_hash,
        execution_receipt_snapshot=receipt_snapshot(current_decision),
    )


def test_receipt_record_replays_complete_continuity_chain():
    record = build()
    replay = replay_continuity_receipt(record)
    assert replay.valid
    assert replay.errors == ()
    assert replay.execution_recorded
    assert replay.decision == ActionDecision.ALLOW


def test_nested_or_chain_tamper_is_detected():
    record = build()
    tampered_decision = record.decision.model_copy(
        update={"reason_codes": ("tampered",)}
    )
    tampered = record.model_copy(update={"decision": tampered_decision})
    replay = replay_continuity_receipt(tampered)
    assert not replay.valid
    assert "decision digest mismatch" in replay.errors
    assert "record digest mismatch" in replay.errors

    broken_chain = record.model_copy(update={"chain_hash": "sha256:bad"})
    assert "chain hash mismatch" in replay_continuity_receipt(broken_chain).errors


def test_receipt_metadata_must_match_exact_continuity_decision():
    current_decision = decision()
    snapshot = receipt_snapshot(current_decision)
    snapshot["metadata"]["continuity_decision_ref"] = "other"
    with pytest.raises(ContinuityContractError, match="metadata mismatch"):
        build_continuity_receipt_record(
            sequence=0,
            basis=basis(),
            triggers=(trigger(),),
            assessment=assessment(),
            decision=current_decision,
            recorded_at=NOW,
            execution_receipt_snapshot=snapshot,
        )


def test_allow_requires_execution_receipt_evidence():
    with pytest.raises(ContinuityContractError, match="requires execution receipt"):
        build_continuity_receipt_record(
            sequence=0,
            basis=basis(),
            triggers=(trigger(),),
            assessment=assessment(),
            decision=decision(),
            recorded_at=NOW,
        )


def test_receipt_chain_detects_order_and_previous_hash_drift():
    first = build()
    second = build(sequence=1, previous_chain_hash=first.chain_hash)
    assert verify_continuity_receipt_chain((first, second)).valid

    reordered = verify_continuity_receipt_chain((second, first))
    assert not reordered.valid
    assert any("sequence mismatch" in error for error in reordered.errors)
    assert any("previous chain mismatch" in error for error in reordered.errors)
