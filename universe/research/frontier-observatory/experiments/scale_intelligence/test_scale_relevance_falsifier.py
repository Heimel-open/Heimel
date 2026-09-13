from scale_relevance_falsifier import evaluate


def row(scale, replicate, capability, auc, margin, *, topology="fixed"):
    return {
        "interaction_scale": scale,
        "replicate": replicate,
        "seed": 100 + replicate,
        "invariants": {
            "node_set": "fixed",
            "topology": topology,
            "initial_state": "fixed",
            "taskset": "fixed",
            "compute_budget": "fixed",
            "update_rule": "fixed",
        },
        "capability": capability,
        "task_relevant_auc": auc,
        "task_relevant_margin": margin,
        "integration": 0.7,
    }


def make(values):
    rows = []
    for scale, metrics in values.items():
        for replicate in range(5):
            rows.append(row(scale, replicate, *metrics))
    return rows


def test_survives_task_relevant_transition():
    rows = make({
        1: (0.62, 0.58, 0.025),
        2: (0.68, 0.62, 0.035),
        4: (0.73, 0.65, 0.045),
        8: (0.81, 0.72, 0.070),
        16: (0.74, 0.66, 0.050),
    })
    result = evaluate(rows)
    assert result["status"] == "NOT_FALSIFIED_BY_DATA"
    assert result["candidate_scale"] == 8


def test_falsifies_if_auc_not_above_high_scale():
    rows = make({
        1: (0.62, 0.58, 0.025),
        2: (0.68, 0.62, 0.035),
        4: (0.73, 0.65, 0.045),
        8: (0.81, 0.67, 0.070),
        16: (0.74, 0.66, 0.050),
    })
    result = evaluate(rows)
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["gates"]["candidate_auc_over_scale_16"] is False


def test_falsifies_if_margin_collapses():
    rows = make({
        1: (0.62, 0.58, 0.025),
        2: (0.68, 0.62, 0.035),
        4: (0.73, 0.65, 0.045),
        8: (0.81, 0.72, 0.020),
        16: (0.74, 0.66, 0.015),
    })
    result = evaluate(rows)
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["gates"]["candidate_margin_floor"] is False


def test_falsifies_flat_capability():
    rows = make({scale: (0.70, 0.70, 0.06) for scale in (1, 2, 4, 8, 16)})
    assert evaluate(rows)["status"] == "FALSIFIED_BY_DATA"


def test_confounded_invariants_are_insufficient():
    rows = make({scale: (0.70, 0.70, 0.06) for scale in (1, 2, 4, 8, 16)})
    rows[-1]["invariants"]["topology"] = "changed"
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"


def test_requires_five_replicates():
    rows = make({scale: (0.70, 0.70, 0.06) for scale in (1, 2, 4, 8, 16)})
    rows = [r for r in rows if not (r["interaction_scale"] == 16 and r["replicate"] == 4)]
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"
