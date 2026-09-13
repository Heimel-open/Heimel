"""Regression tests for the VAIG -> REHT authority boundary."""

import pytest
from fastapi.testclient import TestClient

from src.authority_gate import AuthorityDecision, AuthorityGate, ExecutionRequest
from vaig.aarm import AARMDecision, AARMSignal, AARMVerdict, evaluate_signal
from vaig.agent_loop.gate import GateEvent, vaig_gate
from vaig.api import app


def _allow_signal() -> AARMSignal:
    return AARMSignal(
        risk_class="low",
        uncertainty=0.1,
        reversibility="reversible",
        tool_authority="read",
        task_authority="read",
        drift_score=0.0,
        observation_trust=1.0,
        claims_substantiated=True,
        evidence_valid=True,
    )


def test_aarm_allow_is_explicitly_non_authoritative():
    decision = evaluate_signal(_allow_signal())
    assert decision.verdict is AARMVerdict.ALLOW
    assert decision.execution_authority is False
    assert decision.requires_reht_clearance is True
    assert decision.can_execute is False


def test_aarm_decision_rejects_authority_creation():
    with pytest.raises(ValueError, match="cannot grant execution authority"):
        AARMDecision(
            verdict=AARMVerdict.ALLOW,
            reason="bad",
            signal_digest="a" * 64,
            decision_digest="b" * 64,
            execution_authority=True,
        )


def test_legacy_authority_gate_allow_is_only_evaluation():
    gate = AuthorityGate()
    gate.create_delegation(
        delegator_id="human-owner",
        delegator_role="owner",
        delegatee_id="agent-1",
        scope="read_report",
        policy_id="policy-1",
    )
    result = gate.check_authority(
        ExecutionRequest(
            action_id="a-1",
            action_type="read_report",
            actor="agent-1",
        )
    )
    assert result.decision is AuthorityDecision.ALLOW
    assert result.execution_authority is False
    assert result.requires_reht_clearance is True
    assert result.can_execute is False
    assert "REHT clearance remains required" in result.reasoning


def test_agent_gate_allow_cannot_authorize_effect():
    decision = vaig_gate(
        GateEvent(
            run_id="run-1",
            step_id="step-1",
            event_type="tool_call",
            original_intent="read report",
            current_frame="read report",
            tool_authority="read",
            task_authority="read",
            uncertainty=0.1,
        )
    )
    assert decision.execution_authority is False
    assert decision.requires_reht_clearance is True
    assert decision.can_execute is False


def test_legacy_authorize_endpoint_never_returns_clearance_or_permit():
    client = TestClient(app)
    response = client.post(
        "/api/v1/authorize",
        json={
            "intent": "read report",
            "evidence": {
                "risk_score": 0.1,
                "uncertainty": 0.1,
                "drift_score": 0.0,
                "observation_trust": 1.0,
                "reversibility": "reversible",
                "claims_substantiated": True,
                "evidence_valid": True,
            },
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["evaluation"] == "ALLOW"
    assert payload["decision"] == "ALLOW"  # compatibility alias only
    assert payload["execution_authority"] is False
    assert payload["requires_reht_clearance"] is True
    assert payload["reht_clearance"] is None
    assert payload["permit"] is None
    assert payload["receipt"]["execution_authority"] is False


def test_legacy_authorization_lookup_does_not_fabricate_allow():
    client = TestClient(app)
    payload = client.get("/api/v1/authorization/legacy-1").json()
    assert payload["status"] == "NOT_STORED_BY_VAIG"
    assert payload["execution_authority"] is False
    assert payload["requires_reht_clearance"] is True
    assert "decision" not in payload
