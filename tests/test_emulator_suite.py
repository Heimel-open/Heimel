"""Emulator test suite for Tiny Edge profile:
Verifies mismatch, expiry, mutation, replay, emergency HALT and reconnect behavior.
"""

import pytest
from valo_edge.contracts import (
    EdgeActionProposal,
    OfflineAuthorityEnvelope,
    EdgeDecision,
)
from valo_edge.runtime import MicroRehtEngine
from valo_edge.gateway import HardwareNeutralGateway


def test_mismatch_device_id_denied():
    engine = MicroRehtEngine()
    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-1",
        device_id="dev-authorized",
        allowed_action_types=["PUMP_START"],
        valid_until_iso="2026-08-05T12:00:00Z",
    )
    proposal = EdgeActionProposal(
        proposal_id="prop-mismatch",
        device_id="dev-unauthorized",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:00:00Z",
        nonce="nonce-mismatch-1",
    )
    clearance = engine.evaluate_proposal(proposal, envelope, current_time_iso="2026-08-04T12:00:00Z")
    assert clearance.decision == EdgeDecision.DENY
    assert "Device ID mismatch" in clearance.reason


def test_expired_envelope_denied():
    engine = MicroRehtEngine()
    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-1",
        device_id="dev-1",
        allowed_action_types=["PUMP_START"],
        valid_until_iso="2026-08-03T12:00:00Z",  # Expired yesterday
    )
    proposal = EdgeActionProposal(
        proposal_id="prop-expired",
        device_id="dev-1",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:00:00Z",
        nonce="nonce-expired-1",
    )
    clearance = engine.evaluate_proposal(proposal, envelope, current_time_iso="2026-08-04T12:00:00Z")
    assert clearance.decision == EdgeDecision.DENY
    assert "expired" in clearance.reason


def test_mutation_proposal_hash_mismatch_denied():
    engine = MicroRehtEngine()
    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-1",
        device_id="dev-1",
        allowed_action_types=["PUMP_START"],
        valid_until_iso="2026-08-05T12:00:00Z",
    )
    proposal = EdgeActionProposal(
        proposal_id="prop-mutated",
        device_id="dev-1",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:00:00Z",
        nonce="nonce-mutated-1",
    )
    # Tamper with the proposal hash
    proposal.proposal_hash = "tampered_hash_00000000000000000000000000000000000000000000000000"

    clearance = engine.evaluate_proposal(proposal, envelope, current_time_iso="2026-08-04T12:00:00Z")
    assert clearance.decision == EdgeDecision.DENY
    assert "mutation or hash mismatch" in clearance.reason


def test_replay_attack_denied():
    engine = MicroRehtEngine()
    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-1",
        device_id="dev-1",
        allowed_action_types=["PUMP_START"],
        valid_until_iso="2026-08-05T12:00:00Z",
    )
    proposal1 = EdgeActionProposal(
        proposal_id="prop-1",
        device_id="dev-1",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:00:00Z",
        nonce="nonce-replay-same",
    )
    clearance1 = engine.evaluate_proposal(proposal1, envelope, current_time_iso="2026-08-04T12:00:00Z")
    assert clearance1.decision == EdgeDecision.ALLOW

    # Second proposal reusing exact same nonce
    proposal2 = EdgeActionProposal(
        proposal_id="prop-2",
        device_id="dev-1",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:01:00Z",
        nonce="nonce-replay-same",
    )
    clearance2 = engine.evaluate_proposal(proposal2, envelope, current_time_iso="2026-08-04T12:01:00Z")
    assert clearance2.decision == EdgeDecision.DENY
    assert "Replay attack detected" in clearance2.reason


def test_emergency_halt_state_enforcement():
    engine = MicroRehtEngine()
    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-1",
        device_id="dev-1",
        allowed_action_types=["PUMP_START"],
        valid_until_iso="2026-08-05T12:00:00Z",
    )
    proposal = EdgeActionProposal(
        proposal_id="prop-halt",
        device_id="dev-1",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:00:00Z",
        nonce="nonce-halt-1",
    )

    # Trigger emergency HALT
    engine.trigger_halt("Safety interlock tripped")
    assert engine.is_halted is True

    clearance = engine.evaluate_proposal(proposal, envelope, current_time_iso="2026-08-04T12:00:00Z")
    assert clearance.decision == EdgeDecision.HALT
    assert "HALT" in clearance.reason

    # Gateway enforcement must refuse execution on HALT
    gateway = HardwareNeutralGateway()
    receipt = gateway.execute_action(proposal, clearance, timestamp_iso="2026-08-04T12:00:00Z")
    assert receipt.executed is False
    assert receipt.decision == EdgeDecision.HALT


def test_rate_limit_enforced_per_second():
    engine = MicroRehtEngine()
    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-rate",
        device_id="dev-1",
        allowed_action_types=["PUMP_START"],
        max_rate_per_sec=1,
        valid_until_iso="2026-08-05T12:00:00Z",
    )
    first = EdgeActionProposal(
        proposal_id="prop-rate-1",
        device_id="dev-1",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:00:00Z",
        nonce="nonce-rate-1",
    )
    clearance1 = engine.evaluate_proposal(first, envelope, current_time_iso="2026-08-04T12:00:00Z")
    assert clearance1.decision == EdgeDecision.ALLOW

    second = EdgeActionProposal(
        proposal_id="prop-rate-2",
        device_id="dev-1",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:00:00.500Z",
        nonce="nonce-rate-2",
    )
    clearance2 = engine.evaluate_proposal(second, envelope, current_time_iso="2026-08-04T12:00:00.500Z")
    assert clearance2.decision == EdgeDecision.DENY
    assert "Rate limit exceeded" in clearance2.reason


def test_rate_limit_window_resets_after_one_second():
    engine = MicroRehtEngine()
    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-rate-window",
        device_id="dev-1",
        allowed_action_types=["PUMP_START"],
        max_rate_per_sec=1,
        valid_until_iso="2026-08-05T12:00:00Z",
    )
    first = EdgeActionProposal(
        proposal_id="prop-rate-w-1",
        device_id="dev-1",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:00:00Z",
        nonce="nonce-rate-w-1",
    )
    assert engine.evaluate_proposal(first, envelope, "2026-08-04T12:00:00Z").decision == EdgeDecision.ALLOW

    later = EdgeActionProposal(
        proposal_id="prop-rate-w-2",
        device_id="dev-1",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:02:00Z",
        nonce="nonce-rate-w-2",
    )
    assert engine.evaluate_proposal(later, envelope, "2026-08-04T12:02:00Z").decision == EdgeDecision.ALLOW


def test_seen_nonces_survive_engine_restart(tmp_path):
    state_path = tmp_path / "engine-state.json"
    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-persist",
        device_id="dev-1",
        allowed_action_types=["PUMP_START"],
        valid_until_iso="2026-08-05T12:00:00Z",
    )
    first = EdgeActionProposal(
        proposal_id="prop-persist-1",
        device_id="dev-1",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:00:00Z",
        nonce="nonce-persist-1",
    )
    engine = MicroRehtEngine(state_file=state_path)
    assert engine.evaluate_proposal(first, envelope, "2026-08-04T12:00:00Z").decision == EdgeDecision.ALLOW
    engine.flush()

    reloaded = MicroRehtEngine(state_file=state_path)
    replay = EdgeActionProposal(
        proposal_id="prop-persist-2",
        device_id="dev-1",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:01:00Z",
        nonce="nonce-persist-1",
    )
    clearance = reloaded.evaluate_proposal(replay, envelope, "2026-08-04T12:01:00Z")
    assert clearance.decision == EdgeDecision.DENY
    assert "Replay attack detected" in clearance.reason


def test_gateway_refuses_tampered_clearance_digest():
    engine = MicroRehtEngine()
    envelope = OfflineAuthorityEnvelope(
        envelope_id="env-tamper",
        device_id="dev-1",
        allowed_action_types=["PUMP_START"],
        valid_until_iso="2026-08-05T12:00:00Z",
    )
    proposal = EdgeActionProposal(
        proposal_id="prop-tamper",
        device_id="dev-1",
        action_type="PUMP_START",
        timestamp_iso="2026-08-04T12:00:00Z",
        nonce="nonce-tamper-1",
    )
    clearance = engine.evaluate_proposal(proposal, envelope, "2026-08-04T12:00:00Z")
    assert clearance.decision == EdgeDecision.ALLOW
    clearance.decision = EdgeDecision.DENY

    gateway = HardwareNeutralGateway()
    with pytest.raises(ValueError, match="decision_digest mismatch"):
        gateway.execute_action(proposal, clearance, "2026-08-04T12:00:00Z")
