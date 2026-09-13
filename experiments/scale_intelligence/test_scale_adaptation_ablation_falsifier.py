import pytest

from scale_adaptation_ablation_falsifier import evaluate


INVARIANTS = {
    "node_set": "fixed",
    "topology": "fixed",
    "initial_state": "fixed",
    "taskset": "fixed",
    "compute_budget": "fixed",
    "update_rule": "fixed",
}


def dataset(scores_by_condition, *, mutate=None):
    rows = []
    for scale in (1, 2, 4, 8, 16):
        for replicate in range(3):
            for condition, score in scores_by_condition.items():
                row = {
                    "interaction_scale": scale,
                    "replicate": replicate,
                    "condition": condition,
                    "counterfactual_adaptation": score,
                    "invariants": dict(INVARIANTS),
                }
                if mutate:
                    mutate(row)
                rows.append(row)
    return rows


def test_conjunction_specific_pattern_survives():
    rows = dataset(
        {
            "baseline": 0.04,
            "carryover_only": 0.045,
            "delta_only": 0.048,
            "joint": 0.075,
        }
    )
    result = evaluate(rows)
    assert result["status"] == "NOT_FALSIFIED_BY_DATA"
    assert result["independently_sufficient_at_effect_floor"] == []


def test_delta_only_sufficiency_falsifies_conjunction_claim():
    rows = dataset(
        {
            "baseline": 0.04,
            "carryover_only": 0.035,
            "delta_only": 0.20,
            "joint": 0.075,
        }
    )
    result = evaluate(rows)
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["independently_sufficient_at_effect_floor"] == ["delta_only"]


def test_carryover_only_sufficiency_falsifies_conjunction_claim():
    rows = dataset(
        {
            "baseline": 0.04,
            "carryover_only": 0.08,
            "delta_only": 0.04,
            "joint": 0.075,
        }
    )
    result = evaluate(rows)
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert "carryover_only" in result["independently_sufficient_at_effect_floor"]


def test_joint_failure_falsifies_replication():
    rows = dataset(
        {
            "baseline": 0.04,
            "carryover_only": 0.04,
            "delta_only": 0.04,
            "joint": 0.05,
        }
    )
    result = evaluate(rows)
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert "did not replicate" in result["reason"]


def test_invariant_drift_is_insufficient():
    def mutate(row):
        if row["interaction_scale"] == 8:
            row["invariants"]["topology"] = "changed"

    result = evaluate(dataset({
        "baseline": 0.04,
        "carryover_only": 0.04,
        "delta_only": 0.04,
        "joint": 0.08,
    }, mutate=mutate))
    assert result["status"] == "INSUFFICIENT_EVIDENCE"


def test_missing_factorial_condition_is_insufficient():
    rows = dataset({
        "baseline": 0.04,
        "carryover_only": 0.04,
        "delta_only": 0.04,
        "joint": 0.08,
    })
    rows = [row for row in rows if not (
        row["interaction_scale"] == 4
        and row["replicate"] == 1
        and row["condition"] == "delta_only"
    )]
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"


def test_invalid_score_rejected():
    rows = dataset({
        "baseline": 0.04,
        "carryover_only": 0.04,
        "delta_only": 0.04,
        "joint": 0.08,
    })
    rows[0]["counterfactual_adaptation"] = 1.2
    with pytest.raises(ValueError):
        evaluate(rows)
