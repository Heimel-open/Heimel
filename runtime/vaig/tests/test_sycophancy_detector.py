import tempfile
from pathlib import Path

import pytest

from vaig.ensemble import DistrustLevel, VAIGEnsemble
from vaig.instruments.registry import SLOT_ORDER, best_available
from vaig.instruments.result import InstrumentStatus
from vaig.instruments.sycophancy_detector import SycophancyDetector


OBSERVATION = {
    "conformity_probability": 0.90,
    "flattery_probability": 0.30,
    "truth_displacement_probability": 0.10,
    "evidence_displacement_probability": 0.20,
    "standing_displacement_probability": 0.10,
    "decision_displacement_probability": 0.90,
    "evaluator_id": "syc-eval:model-v1",
    "rubric_id": "ai-sycophancy-governance-v1",
    "observation_digest": "sha256:" + "a" * 64,
}


def test_sycophancy_detector_is_registered():
    assert "sycophancy_detector" in SLOT_ORDER
    instrument = best_available("sycophancy_detector")
    assert isinstance(instrument, SycophancyDetector)


def test_warmth_or_flattery_without_governance_displacement_is_not_risk():
    instrument = SycophancyDetector()
    observation = {
        **OBSERVATION,
        "conformity_probability": 0.10,
        "flattery_probability": 0.98,
        "truth_displacement_probability": 0.0,
        "evidence_displacement_probability": 0.0,
        "standing_displacement_probability": 0.0,
        "decision_displacement_probability": 0.0,
    }

    assert instrument.score(prompt="p", response="r", **observation) == 0.0


def test_conformity_coupled_to_decision_displacement_raises_bounded_risk():
    instrument = SycophancyDetector()

    score = instrument.score(prompt="p", response="r", **OBSERVATION)

    assert score == pytest.approx(0.81)
    assert 0.0 <= score <= 1.0


def test_flattery_is_only_material_when_coupled_to_governance_displacement():
    instrument = SycophancyDetector()
    observation = {
        **OBSERVATION,
        "conformity_probability": 0.10,
        "flattery_probability": 0.80,
        "truth_displacement_probability": 0.0,
        "evidence_displacement_probability": 0.70,
        "standing_displacement_probability": 0.0,
        "decision_displacement_probability": 0.0,
    }

    assert instrument.score(prompt="p", response="r", **observation) == pytest.approx(0.56)


def test_probabilities_and_provenance_bindings_are_required():
    instrument = SycophancyDetector()

    with pytest.raises(ValueError, match="conformity_probability"):
        instrument.score(
            prompt="p",
            response="r",
            **{**OBSERVATION, "conformity_probability": 1.01},
        )
    with pytest.raises(ValueError, match="evaluator_id"):
        instrument.score(
            prompt="p",
            response="r",
            **{**OBSERVATION, "evaluator_id": ""},
        )
    with pytest.raises(ValueError, match="rubric_id"):
        instrument.score(
            prompt="p",
            response="r",
            **{**OBSERVATION, "rubric_id": ""},
        )
    with pytest.raises(ValueError, match="sha256"):
        instrument.score(
            prompt="p",
            response="r",
            **{**OBSERVATION, "observation_digest": "unbound"},
        )


def test_ensemble_feeds_sycophancy_risk_into_existing_distrust_aggregation():
    with tempfile.TemporaryDirectory() as tmp:
        ensemble = VAIGEnsemble(log_path=str(Path(tmp) / "audit.jsonl"))
        result = ensemble.evaluate(
            prompt="prompt",
            response="response",
            active_slots={"sycophancy_detector"},
            required_slots={"sycophancy_detector"},
            instrument_inputs={"sycophancy_detector": OBSERVATION},
        )

    measurement = result.instrument_results["sycophancy_detector"]
    assert measurement.status is InstrumentStatus.MEASURED
    assert measurement.raw_score == pytest.approx(0.81)
    assert result.combined_score == pytest.approx(0.81)
    assert result.level is DistrustLevel.HALT
    assert not hasattr(measurement, "authorize")
    assert not hasattr(measurement, "clearance")
    assert not hasattr(measurement, "execute")


def test_missing_sycophancy_measurement_fails_closed_not_zero_risk():
    missing = {
        key: value
        for key, value in OBSERVATION.items()
        if key != "decision_displacement_probability"
    }
    with tempfile.TemporaryDirectory() as tmp:
        ensemble = VAIGEnsemble(log_path=str(Path(tmp) / "audit.jsonl"))
        result = ensemble.evaluate(
            prompt="prompt",
            response="response",
            active_slots={"sycophancy_detector"},
            required_slots={"sycophancy_detector"},
            instrument_inputs={"sycophancy_detector": missing},
        )

    measurement = result.instrument_results["sycophancy_detector"]
    assert measurement.status is InstrumentStatus.UNAVAILABLE
    assert measurement.raw_score is None
    assert "sycophancy_detector" in result.required_unmeasured
    assert result.level is DistrustLevel.HALT
