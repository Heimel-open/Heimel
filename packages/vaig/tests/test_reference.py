import pytest
from valo_vaig import (
    AuditReceipt,
    DistrustLevel,
    GateDecision,
    PolicyConfig,
    ValidationResult,
    level_to_gate_status,
    load_policy,
)


def test_levels_fail_closed_at_halt():
    assert level_to_gate_status(DistrustLevel.TRUSTED) == "PASS"
    assert level_to_gate_status(DistrustLevel.DEGRADE) == "DEGRADE"
    assert level_to_gate_status(DistrustLevel.HALT) == "HALT"
    assert ValidationResult("entry", DistrustLevel.HALT, 1.0, {}, "hash", 2.0).should_halt


def test_policy_thresholds_are_explicit_and_environment_is_scoped(monkeypatch):
    monkeypatch.setenv("VALO_COHERENCE_THRESHOLD", "0.42")
    policy = load_policy()
    assert policy.coherence_threshold == pytest.approx(0.42)
    assert policy.distrust_thresholds["HALT"] == PolicyConfig().halt_threshold


def test_decision_and_receipt_are_serialisable_shapes():
    decision = GateDecision("PASS", "DEGRADE", 0.9, "fluid")
    assert decision.as_dict()["combined_status"] == "DEGRADE"
    receipt = AuditReceipt.from_dict({"id": "r1", "hash": "h", "source": "test"})
    assert receipt.extra == {"source": "test"}
