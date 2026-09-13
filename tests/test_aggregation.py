"""Tests for VAIG policy-driven aggregation."""

import pytest

from vaig.aggregation import (
    AggregationMode,
    AggregationPolicy,
    aggregate_instrument_results,
)
from vaig.ensemble import DistrustLevel, VAIGEnsemble
from vaig.instruments.result import InstrumentResult, InstrumentStatus


def measured(slot, score):
    return InstrumentResult(
        slot=slot,
        status=InstrumentStatus.MEASURED,
        raw_score=score,
        implementation="test",
    )


class FixedInstrument:
    def __init__(self, value):
        self.value = value

    def score(self, **kwargs):
        return self.value


def test_default_risk_weighted_max_cannot_dilute_critical_signal():
    results = {"critical": measured("critical", 1.0)}
    results.update({f"low_{index}": measured(f"low_{index}", 0.1) for index in range(7)})

    aggregate = aggregate_instrument_results(results)

    assert aggregate.mode is AggregationMode.RISK_WEIGHTED_MAX
    assert aggregate.score == 1.0
    assert aggregate.halt_requested is True
    assert aggregate.vetoed_slots == ("critical",)


def test_hard_veto_records_named_invariant_slot():
    policy = AggregationPolicy(
        mode=AggregationMode.HARD_VETO,
        version="payments-v1",
        hard_veto_slots=("authority_invariant",),
        veto_threshold=0.75,
    )
    results = {
        "authority_invariant": measured("authority_invariant", 0.8),
        "other": measured("other", 0.95),
    }

    aggregate = aggregate_instrument_results(results, policy=policy)

    assert aggregate.score == 0.95
    assert aggregate.halt_requested is True
    assert aggregate.vetoed_slots == ("authority_invariant",)
    assert aggregate.policy_version == "payments-v1"


def test_minority_veto_counts_only_declared_independent_slots():
    policy = AggregationPolicy(
        mode=AggregationMode.MINORITY_VETO,
        version="independent-panel-v1",
        independent_slots=("judge_a", "judge_b", "judge_c"),
        minority_veto_count=2,
        veto_threshold=0.75,
    )
    results = {
        "judge_a": measured("judge_a", 0.8),
        "judge_b": measured("judge_b", 0.9),
        "same_model_copy": measured("same_model_copy", 1.0),
    }

    aggregate = aggregate_instrument_results(results, policy=policy)

    assert aggregate.halt_requested is True
    assert aggregate.vetoed_slots == ("judge_a", "judge_b")
    assert "same_model_copy" not in aggregate.high_severity_slots


def test_minority_veto_does_not_count_undeclared_copy():
    policy = AggregationPolicy(
        mode=AggregationMode.MINORITY_VETO,
        independent_slots=("judge_a", "judge_b"),
        minority_veto_count=2,
        veto_threshold=0.75,
    )
    results = {
        "judge_a": measured("judge_a", 0.8),
        "same_model_copy": measured("same_model_copy", 1.0),
    }

    aggregate = aggregate_instrument_results(results, policy=policy)

    assert aggregate.halt_requested is False
    assert aggregate.high_severity_slots == ("judge_a",)
    assert aggregate.vetoed_slots == ()


def test_calibrated_fusion_without_profile_abstains():
    policy = AggregationPolicy(
        mode=AggregationMode.CALIBRATED_FUSION,
        slot_weights={"a": 1.0},
    )

    aggregate = aggregate_instrument_results({"a": measured("a", 0.2)}, policy=policy)

    assert aggregate.abstained is True
    assert aggregate.halt_requested is True
    assert "calibration profile" in aggregate.abstention_reason


def test_calibrated_fusion_requires_complete_weight_contract():
    policy = AggregationPolicy(
        mode=AggregationMode.CALIBRATED_FUSION,
        calibration_profile="finance-labelled-v1",
        slot_weights={"a": 1.0},
    )
    results = {"a": measured("a", 0.2), "b": measured("b", 0.8)}

    aggregate = aggregate_instrument_results(results, policy=policy)

    assert aggregate.abstained is True
    assert aggregate.halt_requested is True
    assert "every measured slot" in aggregate.abstention_reason


def test_calibrated_fusion_uses_named_profile_and_weights():
    policy = AggregationPolicy(
        mode=AggregationMode.CALIBRATED_FUSION,
        version="fusion-v1",
        calibration_profile="finance-labelled-v1",
        slot_weights={"a": 1.0, "b": 3.0},
        halt_threshold=0.9,
    )
    results = {"a": measured("a", 0.2), "b": measured("b", 0.6)}

    aggregate = aggregate_instrument_results(results, policy=policy)

    assert aggregate.abstained is False
    assert aggregate.score == pytest.approx(0.5)
    assert aggregate.calibration_profile == "finance-labelled-v1"


def test_all_zero_measurements_are_valid_low_risk():
    results = {"a": measured("a", 0.0), "b": measured("b", 0.0)}

    aggregate = aggregate_instrument_results(results)

    assert aggregate.score == 0.0
    assert aggregate.abstained is False
    assert aggregate.halt_requested is False
    assert aggregate.contributing_slots == ("a", "b")


def test_required_unavailable_measurement_abstains():
    results = {
        "required": InstrumentResult(
            slot="required",
            status=InstrumentStatus.UNAVAILABLE,
            failure_reason="missing input",
        )
    }

    aggregate = aggregate_instrument_results(results, required_slots={"required"})

    assert aggregate.abstained is True
    assert aggregate.halt_requested is True
    assert aggregate.unavailable_required_slots == ("required",)
    assert aggregate.score == 0.0


def test_ensemble_default_max_halts_and_records_aggregation(tmp_path):
    ensemble = VAIGEnsemble(log_path=str(tmp_path / "audit.jsonl"))
    ensemble.instruments = {
        "critical": FixedInstrument(1.0),
        **{f"low_{index}": FixedInstrument(0.1) for index in range(7)},
    }

    result = ensemble.evaluate(
        prompt="May this action execute?",
        response="Proceed.",
        active_slots=set(ensemble.instruments),
    )

    assert result.combined_score == 1.0
    assert result.level is DistrustLevel.HALT
    assert result.aggregation.mode is AggregationMode.RISK_WEIGHTED_MAX
    assert result.aggregation.vetoed_slots == ("critical",)

    entry = ensemble.worm.read_all()[0]
    assert entry["aggregation"]["mode"] == "RISK_WEIGHTED_MAX"
    assert entry["aggregation"]["vetoed_slots"] == ["critical"]
