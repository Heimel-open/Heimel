from scale_boundary_falsifier import evaluate

BLOCKS = (5, 9, 13)
SCALES = tuple(range(4, 16))
SEEDS = (1, 2, 3, 4, 5)


def synthetic(interior_peaks=(5, 9, 13), full_cap_peaks=(12, 9, 13)):
    trials = []
    for bi, block in enumerate(BLOCKS):
        for scale in SCALES:
            for replicate, seed in enumerate(SEEDS):
                ep = interior_peaks[bi]
                cp = interior_peaks[bi]
                fcp = full_cap_peaks[bi]
                trials.append(
                    {
                        "task_block": block,
                        "interaction_scale": scale,
                        "replicate": replicate,
                        "seed": seed,
                        "non_geometry_invariants": {"x": "same"},
                        "interior_information_efficiency": max(
                            0.0, 1.0 - 0.02 * abs(scale - ep)
                        ),
                        "interior_capability": max(
                            0.0, 1.0 - 0.02 * abs(scale - cp)
                        ),
                        "full_information_efficiency": max(
                            0.0, 1.0 - 0.02 * abs(scale - ep)
                        ),
                        "full_capability": max(
                            0.0, 1.0 - 0.02 * abs(scale - fcp)
                        ),
                    }
                )
    return trials


def test_boundary_specific_rescue_survives():
    result = evaluate(synthetic())
    assert result["status"] == "NOT_FALSIFIED_BY_DATA"
    assert result["gates"]["interior_peak_relation"] is True
    assert result["gates"]["boundary_specificity"] is True


def test_no_specificity_falsifies():
    result = evaluate(synthetic(full_cap_peaks=(5, 9, 13)))
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["gates"]["boundary_specificity"] is False


def test_interior_failure_falsifies():
    result = evaluate(synthetic(interior_peaks=(7, 10, 9)))
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["gates"]["interior_peak_relation"] is False


def test_missing_region_metric_is_insufficient():
    trials = synthetic()
    del trials[0]["interior_capability"]
    result = evaluate(trials)
    assert result["status"] == "INSUFFICIENT_EVIDENCE"


def test_invariant_drift_is_insufficient():
    trials = synthetic()
    trials[0]["non_geometry_invariants"] = {"x": "drift"}
    result = evaluate(trials)
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
