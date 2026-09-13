import pytest

from scale_adaptation_falsifier import REQUIRED_INVARIANTS, evaluate


def trial(condition, scale, replicate, score, invariant_overrides=None):
    invariants = {name: "fixed" for name in REQUIRED_INVARIANTS}
    if invariant_overrides:
        invariants.update(invariant_overrides)
    return {
        "condition": condition,
        "interaction_scale": scale,
        "replicate": replicate,
        "counterfactual_adaptation": score,
        "invariants": invariants,
    }


def paired_rows(baselines, enabled):
    rows = []
    for scale in (1, 2, 4, 8, 16):
        for replicate in range(3):
            rows.append(trial("baseline", scale, replicate, baselines[scale]))
            rows.append(trial("temporal_carryover", scale, replicate, enabled[scale]))
    return rows


def test_survives_material_paired_gain_across_scales():
    rows = paired_rows(
        {1: .04, 2: .04, 4: .04, 8: .04, 16: .04},
        {1: .07, 2: .08, 4: .08, 8: .08, 16: .07},
    )
    result = evaluate(rows)
    assert result["status"] == "NOT_FALSIFIED_BY_DATA"
    assert result["mean_gain"] >= .02
    assert result["positive_scales"] == 5


def test_no_material_gain_falsifies():
    rows = paired_rows(
        {1: .04, 2: .04, 4: .04, 8: .04, 16: .04},
        {1: .045, 2: .05, 4: .05, 8: .05, 16: .045},
    )
    assert evaluate(rows)["status"] == "FALSIFIED_BY_DATA"


def test_gain_on_too_few_scales_falsifies():
    rows = paired_rows(
        {1: .04, 2: .04, 4: .04, 8: .04, 16: .04},
        {1: .04, 2: .04, 4: .04, 8: .16, 16: .16},
    )
    result = evaluate(rows)
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["positive_scales"] == 2


def test_high_baseline_falsifies_isolation_claim():
    rows = paired_rows(
        {1: .12, 2: .12, 4: .12, 8: .12, 16: .12},
        {1: .16, 2: .16, 4: .16, 8: .16, 16: .16},
    )
    result = evaluate(rows)
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert "baseline adaptation" in result["reason"]


def test_invariant_drift_is_insufficient():
    rows = paired_rows(
        {1: .04, 2: .04, 4: .04, 8: .04, 16: .04},
        {1: .08, 2: .08, 4: .08, 8: .08, 16: .08},
    )
    rows[-1] = trial(
        "temporal_carryover",
        16,
        2,
        .08,
        {"topology": "changed"},
    )
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"


def test_unpaired_replicates_are_insufficient():
    rows = paired_rows(
        {1: .04, 2: .04, 4: .04, 8: .04, 16: .04},
        {1: .08, 2: .08, 4: .08, 8: .08, 16: .08},
    )
    rows = [row for row in rows if not (
        row["condition"] == "temporal_carryover"
        and row["interaction_scale"] == 8
        and row["replicate"] == 2
    )]
    result = evaluate(rows)
    assert result["status"] == "INSUFFICIENT_EVIDENCE"


def test_invalid_score_rejected():
    rows = [trial("baseline", 1, 0, 1.2)]
    with pytest.raises(ValueError):
        evaluate(rows)
