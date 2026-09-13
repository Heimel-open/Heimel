"""
VACS Fidelity runtime tests.

Covers the recovered signed intent session, session state gate, checkpoint, and
recovery manager primitives.
"""

import os
import sys

sys.path.insert(0, "../src")

from checkpoint import CheckpointManager  # noqa: E402
from intent_session import IntentSession  # noqa: E402
from recovery import RecoveryLevel, RecoveryManager  # noqa: E402
from session_key import SessionKeyManager  # noqa: E402
from state_gate import AgentState, SessionStateGate  # noqa: E402


def make_intent(signing_key=None, **overrides):
    signing_key = signing_key or os.urandom(32)
    values = {
        "session_id": "session-123456",
        "intent_id": "intent-update-record",
        "signed_by": "guardian-1",
        "target_schema": "generic-json",
        "allowed_operations": ["modify"],
        "prohibited_operations": ["delete"],
        "max_steps": 3,
    }
    values.update(overrides)
    signature = IntentSession.sign(
        values["session_id"],
        values["intent_id"],
        values["signed_by"],
        values["target_schema"],
        signing_key,
    )
    return IntentSession(signature=signature, **values), signing_key


def test_intent_session_hmac_signature_round_trip():
    intent, signing_key = make_intent()
    assert intent.verify_signature(signing_key)
    assert not intent.verify_signature(os.urandom(32))


def test_intent_session_authority_profile():
    intent, _ = make_intent()
    profile = intent.to_authority_profile()
    assert profile["session_id"] == "session-123456"
    assert profile["signed_by"] == "guardian-1"
    assert profile["allowed_operations"] == ["modify"]
    assert profile["prohibited_operations"] == ["delete"]


def test_session_state_gate_allows_bounded_modify_and_signs_receipt():
    intent, _ = make_intent()
    manager = SessionKeyManager.generate()
    session_key, key_id = manager.derive(intent.session_id)
    gate = SessionStateGate(intent, session_key, key_id)

    previous = AgentState.from_data({"status": "draft"}, step_number=0)
    proposed = AgentState.from_data({"status": "approved"}, step_number=1)

    decision, receipt = gate.evaluate(previous, proposed)

    assert decision == "ALLOW"
    assert receipt.decision == "ALLOW"
    assert receipt.key_id == key_id
    assert receipt.previous_state_hash == previous.state_hash
    assert receipt.proposed_state_hash == proposed.state_hash
    assert receipt.verify(session_key)
    assert not receipt.verify(os.urandom(32))


def test_session_state_gate_denies_prohibited_delete():
    intent, _ = make_intent()
    manager = SessionKeyManager.generate()
    session_key, key_id = manager.derive(intent.session_id)
    gate = SessionStateGate(intent, session_key, key_id)

    previous = AgentState.from_data({"status": "draft", "owner": "a"}, step_number=0)
    proposed = AgentState.from_data({"status": "draft"}, step_number=1)

    decision, receipt = gate.evaluate(previous, proposed)

    assert decision == "DENY"
    assert receipt.verify(session_key)


def test_session_state_gate_steps_up_on_structural_add():
    intent, _ = make_intent(allowed_operations=["modify", "add"])
    manager = SessionKeyManager.generate()
    session_key, key_id = manager.derive(intent.session_id)
    gate = SessionStateGate(intent, session_key, key_id)

    previous = AgentState.from_data({"status": "draft"}, step_number=0)
    proposed = AgentState.from_data({"status": "draft", "new_scope": "extra"}, step_number=1)

    decision, receipt = gate.evaluate(previous, proposed)

    assert decision == "STEP_UP"
    assert receipt.diff_summary["insertions_count"] == 1


def test_session_state_gate_steps_up_after_max_steps():
    intent, _ = make_intent(max_steps=1)
    manager = SessionKeyManager.generate()
    session_key, key_id = manager.derive(intent.session_id)
    gate = SessionStateGate(intent, session_key, key_id)

    previous = AgentState.from_data({"status": "draft"}, step_number=1)
    proposed = AgentState.from_data({"status": "approved"}, step_number=2)

    decision, _ = gate.evaluate(previous, proposed)

    assert decision == "STEP_UP"


def test_checkpoint_manager_checkpoint_and_rollback():
    checkpoints = CheckpointManager("container-a")
    first = checkpoints.checkpoint("start", state_hash="h1")
    second = checkpoints.checkpoint("step_1", state_hash="h2")

    assert first.startswith("cp_start_")
    assert second.startswith("cp_step_1_")
    assert checkpoints.get_active_checkpoint() == second
    assert checkpoints.rollback(first) is True
    assert checkpoints.get_active_checkpoint() == first
    assert checkpoints.rollback("missing") is False
    assert checkpoints.get_stats()["rollback_count"] == 1


def test_recovery_manager_maps_argument_failure_to_modify():
    checkpoints = CheckpointManager("container-a")
    checkpoint_id = checkpoints.checkpoint("step_1", state_hash="h1")
    recovery = RecoveryManager(checkpoints)

    level, decision, rolled_back = recovery.recover("argument_error")

    assert level == RecoveryLevel.ARGUMENT
    assert decision == "MODIFY"
    assert rolled_back == checkpoint_id
    assert checkpoints.get_active_checkpoint() == checkpoint_id


def test_recovery_manager_escalates_after_consecutive_failures():
    checkpoints = CheckpointManager("container-a")
    checkpoints.checkpoint("step_1", state_hash="h1")
    recovery = RecoveryManager(checkpoints)

    recovery.recover("argument_error")
    recovery.recover("argument_error")
    level, decision, _ = recovery.recover("argument_error")

    assert level == RecoveryLevel.ESCALATE
    assert decision == "HALT"
    assert recovery.get_recovery_stats()["escalations"] == 1