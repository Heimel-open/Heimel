"""PR 3 micro-REHT V1 enforcement extensions."""

from __future__ import annotations

import os
from typing import Any, Dict, List
import pytest
from valo_edge.contracts import (
    EdgeActionProposal,
    OfflineAuthorityEnvelope,
    EdgeClearance,
    EdgeDecision,
)
from valo_edge.runtime import MicroRehtEngine


def _envelope() -> OfflineAuthorityEnvelope:
    return OfflineAuthorityEnvelope(
        envelope_id="env-1",
        device_id="dev-1",
        allowed_action_types=["PUMP_START"],
        valid_until_iso="2026-08-05T12:00:00Z",
    )


def _proposal(nonce: str = "nonce-ok") -> EdgeActionProposal:
    proposal = EdgeActionProposal(
        proposal_id="prop-ok",
        device_id="dev-1",
        action_type="PUMP_START",
        parameters={},
        timestamp_iso="2026-08-04T12:00:00Z",
        nonce=nonce,
    )
    return proposal


def test_parameter_schema_enforcement():
    engine = MicroRehtEngine()
    proposal = _proposal()
    proposal.parameters["speed"] = 1.0
    proposal.parameters["evil"] = True
    proposal = EdgeActionProposal(
        proposal_id=proposal.proposal_id,
        device_id=proposal.device_id,
        action_type=proposal.action_type,
        parameters=proposal.parameters,
        timestamp_iso=proposal.timestamp_iso,
        nonce=proposal.nonce,
        proposal_hash=proposal.compute_hash(),
    )
    clearance = engine.evaluate_proposal(
        proposal,
        _envelope(),
        current_time_iso="2026-08-04T12:00:00Z",
        allowed_parameters_schema={"speed": 1.0},
    )
    assert clearance.decision == EdgeDecision.DENY
    assert "Disallowed parameters" in clearance.reason


def test_device_model_firmware_binding():
    engine = MicroRehtEngine()
    proposal = _proposal()
    clearance = engine.evaluate_proposal(
        proposal,
        _envelope(),
        current_time_iso="2026-08-04T12:00:00Z",
        expected_device_binding="sha256:device",
        expected_model_binding="sha256:model",
        expected_firmware_binding="sha256:fw",
    )
    assert clearance.decision == EdgeDecision.DENY
    assert "Device attestation hash" in clearance.reason


def test_state_predicate_failure():
    engine = MicroRehtEngine()
    proposal = _proposal()
    clearance = engine.evaluate_proposal(
        proposal,
        _envelope(),
        current_time_iso="2026-08-04T12:00:00Z",
        state_predicates=[{"field": "door", "equals": "closed"}],
    )
    assert clearance.decision == EdgeDecision.DENY
    assert "State predicate failed" in clearance.reason


def test_sensor_freshness():
    engine = MicroRehtEngine()
    proposal = _proposal()
    clearance = engine.evaluate_proposal(
        proposal,
        _envelope(),
        current_time_iso="2026-08-04T12:00:00Z",
        sensor_provenance={
            "capture_timestamp_iso": "2026-08-04T11:59:00Z",
            "max_age_seconds": 30,
        },
    )
    assert clearance.decision == EdgeDecision.DENY
    assert "stale" in clearance.reason


def test_rate_limit_and_permit_budget():
    engine = MicroRehtEngine()
    proposal = _proposal(nonce="n-rate-1")
    clearance = engine.evaluate_proposal(
        proposal,
        _envelope(),
        current_time_iso="2026-08-04T12:00:00Z",
        max_requests=1,
        rate_limit_seconds=60,
    )
    assert clearance.decision == EdgeDecision.ALLOW

    proposal2 = _proposal(nonce="n-rate-2")
    clearance2 = engine.evaluate_proposal(
        proposal2,
        _envelope(),
        current_time_iso="2026-08-04T12:00:01Z",
        max_requests=1,
        rate_limit_seconds=60,
    )
    assert clearance2.decision == EdgeDecision.DENY
    assert "Rate limit exceeded" in clearance2.reason


def test_permit_budget_exhausted():
    engine = MicroRehtEngine()
    proposal = _proposal(nonce="n-pb-1")
    clearance = engine.evaluate_proposal(
        proposal,
        _envelope(),
        current_time_iso="2026-08-04T12:00:00Z",
        permit_budget={"PUMP_START": 1},
    )
    assert clearance.decision == EdgeDecision.ALLOW

    proposal2 = _proposal(nonce="n-pb-2")
    clearance2 = engine.evaluate_proposal(
        proposal2,
        _envelope(),
        current_time_iso="2026-08-04T12:00:01Z",
        permit_budget={"PUMP_START": 1},
    )
    assert clearance2.decision == EdgeDecision.DENY
    assert "Permit budget exhausted" in clearance2.reason


def test_one_shot_permits():
    engine = MicroRehtEngine()
    proposal = _proposal(nonce="n-shot-1")
    clearance = engine.evaluate_proposal(
        proposal,
        _envelope(),
        current_time_iso="2026-08-04T12:00:00Z",
        one_shot_nonces=["n-shot-1"],
    )
    assert clearance.decision == EdgeDecision.ALLOW

    proposal2 = _proposal(nonce="n-shot-1")
    clearance2 = engine.evaluate_proposal(
        proposal2,
        _envelope(),
        current_time_iso="2026-08-04T12:00:01Z",
        one_shot_nonces=["n-shot-1"],
    )
    assert clearance2.decision == EdgeDecision.DENY
    assert "Replay attack detected" in clearance2.reason


def test_monotonic_decision_preservation():
    engine = MicroRehtEngine()
    proposal = _proposal()
    clearance = engine.evaluate_proposal(
        proposal,
        _envelope(),
        current_time_iso="2026-08-04T12:00:00Z",
    )
    assert clearance.decision == EdgeDecision.ALLOW
    engine._last_decision = EdgeDecision.HALT
    engine._last_proposal_id = proposal.proposal_id
    engine._last_decision_ts = "2026-08-04T12:00:00Z"

    clearance2 = engine.evaluate_proposal(
        proposal,
        _envelope(),
        current_time_iso="2026-08-04T12:00:01Z",
    )
    assert clearance2.decision == EdgeDecision.HALT
    assert "Monotonic preservation" in clearance2.reason


def test_persistence_and_halt_resume(tmp_path: Any):
    state_file = str(tmp_path / "micro_reht.json")
    engine = MicroRehtEngine(state_file=state_file)
    proposal = _proposal(nonce="n-persist")
    clearance = engine.evaluate_proposal(
        proposal,
        _envelope(),
        current_time_iso="2026-08-04T12:00:00Z",
    )
    assert clearance.decision == EdgeDecision.ALLOW
    engine.trigger_halt("safety")

    reloaded = MicroRehtEngine(state_file=state_file)
    assert reloaded.is_halted is True
    proposal2 = _proposal(nonce="n-persist-2")
    clearance2 = reloaded.evaluate_proposal(
        proposal2,
        _envelope(),
        current_time_iso="2026-08-04T12:00:01Z",
    )
    assert clearance2.decision == EdgeDecision.HALT
