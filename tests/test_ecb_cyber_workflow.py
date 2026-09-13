"""Integration test: ECB Cyber workflow (#218) uses only canonical authority types.

Proves the workflow drives VAIG evaluation -> REHT clearance -> Receipt without
introducing a duplicate authority contract.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.valo_platform.finserv.ecb_cyber.models import (
    Approval,
    ApprovalLevel,
    ControlException,
    CyberEvaluation,
)
from src.valo_platform.finserv.ecb_cyber.workflow import EcbCyberWorkflow
from src.valo_platform.action_envelope.models import (
    ActionDecision,
    ClearanceState,
    GovernanceClearance,
)


def _approval(action_id: str) -> Approval:
    return Approval(
        approval_id=f"apr-{action_id}",
        action_id=action_id,
        approved_by="CRO",
        level=ApprovalLevel.LEVEL_2,
        decided=ActionDecision.ALLOW,
        at=datetime(2026, 7, 12, tzinfo=timezone.utc),
        conditions=["time-bound"],
        expiry=datetime(2026, 10, 31, tzinfo=timezone.utc),
    )


def test_workflow_uses_canonical_authority_types():
    wf = EcbCyberWorkflow()

    # VAIG side — risk signal only
    ev = wf.evaluate_action(
        action_id="act-1",
        tenant_id="meridian-euro-bank",
        signals=[{"type": "tpr", "confidence": 0.3}],
        risk_tier="LOW",
        authority="chain-001",
    )
    assert isinstance(ev, CyberEvaluation)
    assert ev.recommended_disposition == "allow"

    # REHT side — canonical clearance (sole authority)
    clr = wf.clear_action(
        action_id="act-1",
        tenant_id="meridian-euro-bank",
        evaluation=ev,
        authority="chain-001",
        evidence_refs=["ev-1"],
    )
    assert isinstance(clr, GovernanceClearance)
    # canonical artifact, not a redefined local one
    assert clr.__module__.endswith("action_envelope.models")
    assert clr.decision in (ActionDecision.ALLOW, ActionDecision.DEFER, ActionDecision.HALT)
    assert clr.state is ClearanceState.ACTIVE
    assert "VAIG" in clr.evaluator_refs and "REHT" in clr.evaluator_refs

    # VAIG and REHT types are DISTINCT (clear boundary)
    assert CyberEvaluation is not GovernanceClearance

    # Human approval -> canonical Receipt
    receipt = wf.record_approval(_approval("act-1"), clr)
    assert receipt.request_id == "act-1"
    assert receipt.action_id == "act-1"

    # Control exception -> canonical Receipt (audit trail)
    exc = ControlException(
        exception_id="exc-1", control_id="ctrl-1", reason="temp",
        approved_by="CRO", expires=datetime(2026, 12, 1, tzinfo=timezone.utc),
        receipt_signature="sig",
    )
    exc_receipt = wf.record_exception(exc)
    assert exc_receipt.request_id == "ctrl-1"
