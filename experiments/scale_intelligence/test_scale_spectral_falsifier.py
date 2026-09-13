from scale_spectral_falsifier import evaluate

SCALES = tuple(range(4, 16))
CONDS = ("reflected", "self_padded")
TASKS = (
    "seg_b7", "seg_b10", "seg_b13",
    "markov_b3_l8", "markov_b3_l11", "markov_b3_l14",
    "markov_b6_l8", "markov_b6_l11", "markov_b6_l14",
)
SEEDS = (1,2,3,4,5)


def synthetic(offset=0):
    rows = []
    for ci, condition in enumerate(CONDS):
        for ti, task in enumerate(TASKS):
            peak = 5 + (ti % 6)
            capability_peak = peak + offset
            for scale in SCALES:
                for replicate, seed in enumerate(SEEDS):
                    rows.append({
                        "boundary_condition": condition,
                        "task_id": task,
                        "interaction_scale": scale,
                        "replicate": replicate,
                        "seed": seed,
                        "condition_invariants": {"condition": condition},
                        "spectral_target_fraction": max(0.0, 1.0 - 0.02*abs(scale-peak)),
                        "capability": max(0.0, 1.0 - 0.02*abs(scale-capability_peak)),
                        "residual_power": min(1.0, 0.1 + 0.01*abs(scale-peak)),
                        "decomposition_max_error": 0.0,
                    })
    return rows


def test_matching_survives():
    assert evaluate(synthetic())["status"] == "NOT_FALSIFIED_BY_DATA"


def test_large_peak_offset_falsifies():
    assert evaluate(synthetic(offset=3))["status"] == "FALSIFIED_BY_DATA"


def test_decomposition_failure_is_insufficient():
    rows = synthetic()
    rows[0]["decomposition_max_error"] = 1e-6
    r = evaluate(rows)
    assert r["status"] == "INSUFFICIENT_EVIDENCE"
    assert r["reason"] == "operator_decomposition_failed"


def test_missing_condition_is_insufficient():
    rows = [r for r in synthetic() if r["boundary_condition"] == "reflected"]
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"


def test_invariant_drift_is_insufficient():
    rows = synthetic()
    rows[0]["condition_invariants"] = {"condition": "drift"}
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"
