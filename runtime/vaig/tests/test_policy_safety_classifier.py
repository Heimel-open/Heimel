import tempfile
from pathlib import Path

import pytest

from vaig.ensemble import DistrustLevel, VAIGEnsemble
from vaig.instruments.policy_safety_classifier import PolicySafetyClassifier
from vaig.instruments.result import InstrumentStatus
from vaig.instruments.registry import SLOT_ORDER, best_available


OBSERVATION = {
    "unsafe_probability": 0.81,
    "classifier_id": "shieldstral-compatible:model-v1",
    "policy_id": "policy:enterprise-safety-v3",
    "observation_digest": "sha256:" + "a" * 64,
}


def test_policy_safety_classifier_is_registered():
    assert "policy_safety_classifier" in SLOT_ORDER
    instrument = best_available("policy_safety_classifier")
    assert isinstance(instrument, PolicySafetyClassifier)


def test_policy_safety_classifier_returns_bounded_measurement():
    instrument = PolicySafetyClassifier()

    assert instrument.score(prompt="p", response="r", **OBSERVATION) == 0.81

    with pytest.raises(ValueError, match="unsafe_probability"):
        instrument.score(
            prompt="p",
            response="r",
            **{**OBSERVATION, "unsafe_probability": 1.01},
        )


def test_policy_and_classifier_bindings_are_required():
    instrument = PolicySafetyClassifier()

    with pytest.raises(ValueError, match="classifier_id"):
        instrument.score(
            prompt="p",
            response="r",
            **{**OBSERVATION, "classifier_id": ""},
        )
    with pytest.raises(ValueError, match="policy_id"):
        instrument.score(
            prompt="p",
            response="r",
            **{**OBSERVATION, "policy_id": ""},
        )
    with pytest.raises(ValueError, match="sha256"):
        instrument.score(
            prompt="p",
            response="r",
            **{**OBSERVATION, "observation_digest": "unbound"},
        )


def test_ensemble_consumes_classifier_as_measurement_only():
    with tempfile.TemporaryDirectory() as tmp:
        ensemble = VAIGEnsemble(log_path=str(Path(tmp) / "audit.jsonl"))
        result = ensemble.evaluate(
            prompt="prompt",
            response="response",
            active_slots={"policy_safety_classifier"},
            required_slots={"policy_safety_classifier"},
            instrument_inputs={"policy_safety_classifier": OBSERVATION},
        )

    measurement = result.instrument_results["policy_safety_classifier"]
    assert measurement.status is InstrumentStatus.MEASURED
    assert measurement.raw_score == 0.81
    assert result.level is DistrustLevel.HALT
    assert not hasattr(measurement, "authorize")
    assert not hasattr(measurement, "clearance")


def test_missing_classifier_measurement_fails_closed_not_zero_risk():
    missing_probability = {key: value for key, value in OBSERVATION.items() if key != "unsafe_probability"}
    with tempfile.TemporaryDirectory() as tmp:
        ensemble = VAIGEnsemble(log_path=str(Path(tmp) / "audit.jsonl"))
        result = ensemble.evaluate(
            prompt="prompt",
            response="response",
            active_slots={"policy_safety_classifier"},
            required_slots={"policy_safety_classifier"},
            instrument_inputs={"policy_safety_classifier": missing_probability},
        )

    measurement = result.instrument_results["policy_safety_classifier"]
    assert measurement.status is InstrumentStatus.UNAVAILABLE
    assert measurement.raw_score is None
    assert "policy_safety_classifier" in result.required_unmeasured
    assert result.level is DistrustLevel.HALT
