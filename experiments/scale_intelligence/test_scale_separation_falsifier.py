from scale_separation_falsifier import INTEGRATION_METRICS, evaluate


def trial(scale, values, replicate=0, invariant_overrides=None):
    invariants = {
        "node_set": "fixed",
        "topology": "fixed",
        "initial_state": "fixed",
        "taskset": "fixed",
        "compute_budget": "fixed",
        "update_rule": "fixed",
    }
    if invariant_overrides:
        invariants.update(invariant_overrides)
    return {
        "interaction_scale": scale,
        "replicate": replicate,
        "invariants": invariants,
        "phenotype": values,
    }


def values(task, transfer, integration, adaptation):
    return {
        "task_success": task,
        "cross_context_transfer": transfer,
        "distributed_integration": integration,
        "counterfactual_adaptation": adaptation,
    }


def add_scale(rows, scale, phenotype):
    for replicate in range(3):
        rows.append(trial(scale, phenotype, replicate))


def test_survives_when_integration_is_scale_sensitive_and_adaptation_flat_low():
    rows = []
    add_scale(rows, 1, values(0.40, 0.42, 0.50, 0.04))
    add_scale(rows, 2, values(0.50, 0.52, 0.60, 0.04))
    add_scale(rows, 4, values(0.60, 0.63, 0.70, 0.05))
    add_scale(rows, 8, values(0.72, 0.74, 0.80, 0.04))
    add_scale(rows, 16, values(0.58, 0.60, 0.68, 0.04))
    result = evaluate(rows)
    assert result["status"] == "NOT_FALSIFIED_BY_DATA"
    assert result["common_peak_scale"] == 8


def test_falsifies_when_integration_is_flat():
    rows = []
    for scale in (1, 2, 4, 8, 16):
        add_scale(rows, scale, values(0.60, 0.60, 0.60, 0.04))
    assert evaluate(rows)["status"] == "FALSIFIED_BY_DATA"


def test_falsifies_when_adaptation_changes_with_scale():
    rows = []
    adaptations = {1: 0.03, 2: 0.04, 4: 0.07, 8: 0.15, 16: 0.20}
    for scale in (1, 2, 4, 8, 16):
        add_scale(rows, scale, values(0.40 + scale / 50, 0.42 + scale / 50, 0.50 + scale / 50, adaptations[scale]))
    result = evaluate(rows, common_peak_min_metrics=1)
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert "counterfactual adaptation" in result["reason"]


def test_confounded_invariants_are_insufficient():
    rows = []
    for scale in (1, 2, 4, 8, 16):
        for replicate in range(3):
            overrides = {"topology": "changed"} if scale == 8 else None
            rows.append(trial(scale, values(0.4, 0.4, 0.5, 0.04), replicate, overrides))
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"


def test_requires_all_three_integration_metrics_to_be_scale_sensitive():
    rows = []
    for scale, task, transfer in ((1, .4, .4), (2, .5, .5), (4, .6, .6), (8, .75, .75), (16, .55, .55)):
        add_scale(rows, scale, values(task, transfer, 0.60, 0.04))
    result = evaluate(rows)
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["scale_sensitive"]["distributed_integration"] is False


def test_requires_common_peak_for_at_least_two_metrics():
    rows = []
    payload = {
        1: values(.40, .40, .40, .04),
        2: values(.75, .50, .50, .04),
        4: values(.55, .78, .55, .04),
        8: values(.60, .60, .80, .04),
        16: values(.50, .50, .50, .04),
    }
    for scale in (1, 2, 4, 8, 16):
        add_scale(rows, scale, payload[scale])
    result = evaluate(rows)
    assert result["status"] == "FALSIFIED_BY_DATA"
