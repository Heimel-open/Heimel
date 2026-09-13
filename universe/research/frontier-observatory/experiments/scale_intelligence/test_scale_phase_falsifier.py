import pytest

from scale_phase_falsifier import METRICS, REQUIRED_INVARIANTS, evaluate


def trial(scale, value, replicate=0, invariant_overrides=None):
    invariants = {name: "fixed" for name in REQUIRED_INVARIANTS}
    if invariant_overrides:
        invariants.update(invariant_overrides)
    return {
        "interaction_scale": scale,
        "replicate": replicate,
        "invariants": invariants,
        "phenotype": {metric: value for metric in METRICS},
    }


def add_scale(trials, scale, values, invariant_overrides=None):
    for replicate, value in enumerate(values):
        trials.append(
            trial(scale, value, replicate, invariant_overrides=invariant_overrides)
        )


def test_detects_scale_dependent_regime_under_fixed_invariants():
    trials = []
    add_scale(trials, 1.0, (0.30, 0.35, 0.40))
    add_scale(trials, 2.0, (0.75, 0.78, 0.80))
    add_scale(trials, 4.0, (0.82, 0.84, 0.81))

    result = evaluate(trials)

    assert result["status"] == "NOT_FALSIFIED_BY_DATA"
    assert result["direction"] == "emerges_with_scale"
    assert result["scale_margin_observed"] >= 0.15


def test_flat_high_performance_falsifies_scale_dependence():
    trials = []
    add_scale(trials, 1.0, (0.80, 0.82, 0.81))
    add_scale(trials, 2.0, (0.81, 0.83, 0.80))
    add_scale(trials, 4.0, (0.82, 0.80, 0.81))

    result = evaluate(trials)

    assert result["status"] == "FALSIFIED_BY_DATA"
    assert "present across all tested scales" in result["reason"]


def test_flat_low_performance_falsifies_tested_range():
    trials = []
    add_scale(trials, 1.0, (0.30, 0.35, 0.40))
    add_scale(trials, 2.0, (0.40, 0.45, 0.42))
    add_scale(trials, 4.0, (0.50, 0.55, 0.52))

    result = evaluate(trials)

    assert result["status"] == "FALSIFIED_BY_DATA"
    assert "no tested scale" in result["reason"]


def test_non_scale_invariant_drift_is_insufficient():
    trials = []
    add_scale(trials, 1.0, (0.30, 0.35, 0.40))
    add_scale(
        trials,
        2.0,
        (0.75, 0.78, 0.80),
        invariant_overrides={"topology": "changed"},
    )
    add_scale(trials, 4.0, (0.82, 0.84, 0.81))

    result = evaluate(trials)

    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert "invariants changed" in result["reason"]


def test_requires_three_well_replicated_scales():
    trials = []
    add_scale(trials, 1.0, (0.30, 0.35, 0.40))
    add_scale(trials, 2.0, (0.75, 0.78, 0.80))
    add_scale(trials, 4.0, (0.82,))

    result = evaluate(trials)

    assert result["status"] == "INSUFFICIENT_EVIDENCE"


def test_invalid_metric_is_rejected():
    trials = []
    add_scale(trials, 1.0, (1.20, 1.20, 1.20))
    add_scale(trials, 2.0, (0.75, 0.78, 0.80))
    add_scale(trials, 4.0, (0.82, 0.84, 0.81))

    with pytest.raises(ValueError):
        evaluate(trials)
