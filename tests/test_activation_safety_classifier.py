import pytest

from vaig.instruments.activation_safety_classifier import ActivationSafetyClassifier


def _digest():
    return "sha256:" + "a" * 64


def test_activation_safety_classifier_returns_bound_probability():
    instrument = ActivationSafetyClassifier()
    score = instrument.score(
        "prompt",
        "response",
        activation_unsafe_probability=0.73,
        activation_classifier_id="hidden-harm-v1",
        activation_calibration_id="cal-2026-08-11",
        activation_observation_digest=_digest(),
    )
    assert score == 0.73


@pytest.mark.parametrize("value", [-0.01, 1.01, float("inf"), float("nan")])
def test_activation_safety_classifier_rejects_invalid_probability(value):
    instrument = ActivationSafetyClassifier()
    with pytest.raises(ValueError):
        instrument.score(
            "prompt",
            "response",
            activation_unsafe_probability=value,
            activation_classifier_id="hidden-harm-v1",
            activation_calibration_id="cal-2026-08-11",
            activation_observation_digest=_digest(),
        )


def test_activation_safety_classifier_requires_sha256_binding():
    instrument = ActivationSafetyClassifier()
    with pytest.raises(ValueError):
        instrument.score(
            "prompt",
            "response",
            activation_unsafe_probability=0.2,
            activation_classifier_id="hidden-harm-v1",
            activation_calibration_id="cal-2026-08-11",
            activation_observation_digest="not-a-digest",
        )
