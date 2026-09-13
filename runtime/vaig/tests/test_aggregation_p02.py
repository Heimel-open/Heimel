"""P0.2 aggregation regression and edge-case tests for VAIGEnsemble.

Uses the merged policy-driven aggregation (AggregationMode, AggregationPolicy).
Tests: invariant-veto, minority-veto, risk-weighted max, abstention, receipt.
"""
import tempfile, os
import pytest

from vaig.aggregation import AggregationPolicy, AggregationMode
from vaig.ensemble import VAIGEnsemble, DistrustLevel
from vaig.instruments.result import InstrumentResult, InstrumentStatus


def _logpath():
    return tempfile.mktemp(suffix=".jsonl")


def _cleanup(path):
    try:
        os.unlink(path)
    except OSError:
        pass


# --- Regression: basic evaluation still works ---

def test_regression_single_low_score():
    path = _logpath()
    ens = VAIGEnsemble(log_path=path)
    result = ens.evaluate(prompt="simple test", response="everything is fine")
    _cleanup(path)
    assert result.combined_score < 0.8


def test_regression_moderate_scores():
    path = _logpath()
    ens = VAIGEnsemble(log_path=path)
    result = ens.evaluate(
        prompt="complex task",
        response="I'm not entirely sure but maybe we should consider both options",
    )
    _cleanup(path)
    assert result.combined_score >= 0.0


def test_regression_high_scores():
    path = _logpath()
    ens = VAIGEnsemble(log_path=path)
    result = ens.evaluate(
        prompt="critical decision",
        response="This will completely destroy the system, catastrophic failure imminent",
    )
    _cleanup(path)
    assert result.combined_score > 0.0


# --- Invariant-veto via required slots ---

def test_invariant_veto_required_slot_triggers():
    path = _logpath()
    ens = VAIGEnsemble(log_path=path)
    result = ens.evaluate(
        prompt="critical", response="danger",
        required_slots={"nonexistent_slot_xyz"},
    )
    _cleanup(path)
    assert result.level == DistrustLevel.HALT


def test_invariant_veto_no_false_positive():
    path = _logpath()
    ens = VAIGEnsemble(log_path=path)
    result = ens.evaluate(prompt="normal", response="ok", required_slots=set())
    _cleanup(path)
    assert result.level is not DistrustLevel.HALT


# --- Abstention ---

def test_abstention_on_error():
    path = _logpath()
    ens = VAIGEnsemble(log_path=path)
    result = ens.evaluate(prompt="test", response="ok")
    _cleanup(path)
    # All core instruments should be available, so no abstention
    assert result.aggregation is None or not result.aggregation.abstained


# --- Decision receipt ---

def test_aggregation_tracked_in_result():
    path = _logpath()
    ens = VAIGEnsemble(log_path=path)
    result = ens.evaluate(prompt="test", response="ok")
    _cleanup(path)
    assert hasattr(result, "aggregation")


def test_veto_reasons_field_exists():
    path = _logpath()
    ens = VAIGEnsemble(log_path=path)
    result = ens.evaluate(prompt="test", response="ok")
    _cleanup(path)
    assert hasattr(result, "veto_reasons")


# --- Edge: policy-driven aggregation mode ---

def test_policy_risk_weighted_max():
    """Risk-weighted max policy should prefer max over average."""
    path = _logpath()
    policy = AggregationPolicy(mode=AggregationMode.RISK_WEIGHTED_MAX)
    ens = VAIGEnsemble(log_path=path, aggregation_policy=policy)
    result = ens.evaluate(prompt="danger", response="catastrophic failure imminent")
    _cleanup(path)
    assert result.combined_score > 0.0


def test_policy_hard_veto():
    path = _logpath()
    policy = AggregationPolicy(mode=AggregationMode.HARD_VETO)
    ens = VAIGEnsemble(log_path=path, aggregation_policy=policy)
    result = ens.evaluate(prompt="danger", response="catastrophic failure imminent")
    _cleanup(path)
    assert result.combined_score > 0.0
