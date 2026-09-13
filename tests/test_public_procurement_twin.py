from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from valo_platform.public_procurement.twin import (
    ProcurementLifecycleStage,
    ProcurementTraceEvent,
    ProcurementTwinRole,
    ProcurementTwinSnapshot,
    build_procurement_trace_event,
    build_procurement_twin_snapshot,
)


NOW = datetime(2026, 7, 29, 20, 30, tzinfo=timezone.utc)
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


def trace_events():
    return (
        build_procurement_trace_event(
            sequence=1,
            event_id="event:needs-plan",
            stage=ProcurementLifecycleStage.NEEDS_PLAN,
            object_ref="needs-plan:2026-001",
            status="approved",
            summary="Need approved for market publication",
            occurred_at=NOW,
            actor_ref="user:buyer:1",
            evidence_refs=("evidence:need:1",),
            protected_details={"internal_budget_ref": "budget:secret:1"},
        ),
        build_procurement_trace_event(
            sequence=2,
            event_id="event:award",
            stage=ProcurementLifecycleStage.AWARD,
            object_ref="award:2026-001",
            status="step_up_required",
            summary="Award requires human approval before commit",
            occurred_at=NOW + timedelta(hours=1),
            actor_ref="agent:evaluator:1",
            action_case_digest=DIGEST_A,
            clearance_ref="clearance:award:1",
            evidence_refs=("evidence:evaluation:1", "evidence:eligibility:1"),
            evidence_gaps=("human_approval",),
            pending_action="Approve award decision",
            attention_required=True,
            protected_details={"supplier_bank_account": "NO00-SECRET"},
        ),
        build_procurement_trace_event(
            sequence=3,
            event_id="event:contract",
            stage=ProcurementLifecycleStage.CONTRACT,
            object_ref="contract:2026-001",
            status="signed",
            summary="Contract committed after current REHT clearance",
            occurred_at=NOW + timedelta(hours=2),
            actor_ref="user:approver:1",
            action_case_digest=DIGEST_A,
            clearance_ref="clearance:contract:1",
            execution_receipt_ref="receipt:execution:contract:1",
        ),
        build_procurement_trace_event(
            sequence=4,
            event_id="event:payment",
            stage=ProcurementLifecycleStage.PAYMENT,
            object_ref="payment:INV-1",
            status="executed",
            summary="Verified supplier payment executed",
            occurred_at=NOW + timedelta(days=30),
            actor_ref="service:erp:1",
            action_case_digest=DIGEST_B,
            clearance_ref="clearance:payment:1",
            execution_receipt_ref="receipt:execution:payment:1",
            outcome_receipt_ref="receipt:outcome:payment:1",
            protected_details={"bank_account": "NO00-SECRET"},
        ),
        build_procurement_trace_event(
            sequence=5,
            event_id="event:performance",
            stage=ProcurementLifecycleStage.PERFORMANCE,
            object_ref="outcome:contract:2026-001",
            status="on_track",
            summary="Contract performance is on target",
            occurred_at=NOW + timedelta(days=60),
            outcome_receipt_ref="receipt:outcome:performance:1",
            evidence_refs=("evidence:performance:1",),
        ),
        build_procurement_trace_event(
            sequence=6,
            event_id="event:publication",
            stage=ProcurementLifecycleStage.PUBLICATION,
            object_ref="publication:2026-001",
            status="prepared",
            summary="Lifecycle publication payload prepared for data-space adapter",
            occurred_at=NOW + timedelta(days=61),
            clearance_ref="clearance:publication:1",
            pending_action="Publish lifecycle data",
            attention_required=True,
        ),
    )


def snapshot(role: ProcurementTwinRole, *, as_of=NOW + timedelta(days=61)):
    return build_procurement_twin_snapshot(
        tenant_id="tenant:buyer-1",
        procedure_ref="procedure:2026-001",
        role=role,
        events=trace_events(),
        as_of=as_of,
    )


def test_buyer_view_preserves_operational_detail_and_full_trace() -> None:
    result = snapshot(ProcurementTwinRole.BUYER)

    assert result.current_stage is ProcurementLifecycleStage.PUBLICATION
    assert len(result.events) == 6
    assert result.events[0].protected_details["internal_budget_ref"] == "budget:secret:1"
    assert result.events[1].pending_action == "Approve award decision"
    assert result.evidence_gaps == ("human_approval",)
    assert result.attention_count == 2
    assert result.read_only is True
    assert result.grants_authority is False


def test_approver_view_hides_protected_details_but_keeps_decision_inputs() -> None:
    result = snapshot(ProcurementTwinRole.APPROVER)
    award = result.events[1]

    assert award.protected_details == {}
    assert award.actor_ref == "agent:evaluator:1"
    assert award.evidence_refs == ("evidence:eligibility:1", "evidence:evaluation:1")
    assert award.evidence_gaps == ("human_approval",)
    assert award.pending_action == "Approve award decision"


def test_auditor_view_minimizes_personal_and_operational_detail() -> None:
    result = snapshot(ProcurementTwinRole.AUDITOR)
    award = result.events[1]

    assert award.actor_ref is None
    assert award.evidence_refs == ()
    assert award.evidence_gaps == ()
    assert award.pending_action is None
    assert award.protected_details == {}
    assert award.action_case_digest == DIGEST_A
    assert award.clearance_ref == "clearance:award:1"
    assert award.source_event_digest.startswith("sha256:")
    assert "receipt:execution:payment:1" in result.receipt_refs


def test_snapshot_digest_is_stable_across_view_generation_time() -> None:
    first = snapshot(ProcurementTwinRole.AUDITOR, as_of=NOW + timedelta(days=61))
    second = snapshot(ProcurementTwinRole.AUDITOR, as_of=NOW + timedelta(days=62))

    assert first.snapshot_digest == second.snapshot_digest


def test_as_of_snapshot_excludes_future_events() -> None:
    result = snapshot(ProcurementTwinRole.BUYER, as_of=NOW + timedelta(hours=1))

    assert len(result.events) == 2
    assert result.current_stage is ProcurementLifecycleStage.AWARD
    assert "receipt:execution:contract:1" not in result.receipt_refs


def test_non_contiguous_trace_is_rejected() -> None:
    events = trace_events()
    broken = (events[0], events[2])

    with pytest.raises(ValueError, match="contiguous"):
        build_procurement_twin_snapshot(
            tenant_id="tenant:buyer-1",
            procedure_ref="procedure:2026-001",
            role=ProcurementTwinRole.BUYER,
            events=broken,
            as_of=NOW + timedelta(hours=3),
        )


def test_trace_event_digest_rejects_tampering() -> None:
    event = trace_events()[1]
    payload = event.model_dump(mode="json")
    payload["status"] = "tampered"

    with pytest.raises(ValidationError, match="event_digest"):
        ProcurementTraceEvent(**payload)


def test_snapshot_cannot_be_write_enabled_or_grant_authority() -> None:
    result = snapshot(ProcurementTwinRole.BUYER)

    payload = result.model_dump(mode="json")
    payload["read_only"] = False
    with pytest.raises(ValidationError, match="read-only"):
        ProcurementTwinSnapshot(**payload)

    payload = result.model_dump(mode="json")
    payload["grants_authority"] = True
    with pytest.raises(ValidationError, match="cannot grant authority"):
        ProcurementTwinSnapshot(**payload)


def test_receipt_trace_covers_clearance_execution_and_outcome() -> None:
    result = snapshot(ProcurementTwinRole.AUDITOR)

    assert "clearance:contract:1" in result.receipt_refs
    assert "receipt:execution:contract:1" in result.receipt_refs
    assert "receipt:outcome:payment:1" in result.receipt_refs
    assert "receipt:outcome:performance:1" in result.receipt_refs
