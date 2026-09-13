from scale_order_falsifier import evaluate


def row(scale, replicate, integration, differentiation, capability, balance, topology="fixed"):
    return {
        "interaction_scale": scale,
        "replicate": replicate,
        "invariants": {
            "node_set": "fixed",
            "topology": topology,
            "initial_state": "fixed",
            "taskset": "fixed",
            "compute_budget": "fixed",
            "update_rule": "fixed",
        },
        "integration": integration,
        "differentiation": differentiation,
        "capability": capability,
        "balance": balance,
    }


def dataset(values):
    rows = []
    for scale, metrics in values.items():
        for replicate in range(5):
            rows.append(row(scale, replicate, *metrics))
    return rows


def passing_values():
    return {
        1: (0.45, 0.90, 0.52, 0.60),
        2: (0.60, 0.82, 0.65, 0.69),
        4: (0.74, 0.70, 0.76, 0.72),
        8: (0.82, 0.62, 0.86, 0.71),
        16: (0.76, 0.48, 0.73, 0.59),
    }


def test_survives_transition_zone_pattern():
    result = evaluate(dataset(passing_values()))
    assert result["status"] == "NOT_FALSIFIED_BY_DATA"
    assert result["peak_scale"] == 8


def test_falsifies_when_high_extreme_matches_peak_capability():
    values = passing_values()
    values[16] = (0.76, 0.48, 0.84, 0.59)
    assert evaluate(dataset(values))["status"] == "FALSIFIED_BY_DATA"


def test_falsifies_when_low_scale_integration_not_lower():
    values = passing_values()
    values[1] = (0.80, 0.90, 0.52, 0.60)
    result = evaluate(dataset(values))
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["gates"]["integration_above_low_extreme"] is False


def test_falsifies_when_high_scale_differentiation_not_lower():
    values = passing_values()
    values[16] = (0.76, 0.60, 0.73, 0.67)
    result = evaluate(dataset(values))
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["gates"]["differentiation_above_high_extreme"] is False


def test_falsifies_when_capability_peak_outside_balance_zone():
    values = passing_values()
    values[4] = (0.74, 0.70, 0.76, 0.82)
    result = evaluate(dataset(values))
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["gates"]["peak_lies_in_balance_zone"] is False


def test_confounded_invariants_are_insufficient():
    rows = dataset(passing_values())
    rows[-1]["invariants"]["topology"] = "changed"
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"


def test_missing_replicates_are_insufficient():
    rows = dataset(passing_values())
    rows = [row for row in rows if not (row["interaction_scale"] == 16 and row["replicate"] == 4)]
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"
