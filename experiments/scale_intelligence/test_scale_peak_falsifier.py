from scale_peak_falsifier import evaluate

BLOCKS = (5, 9, 13)
SCALES = tuple(range(4, 16))
SEEDS = (1, 2, 3, 4, 5)


def synthetic(e_peaks=(6, 9, 12), c_peaks=(6, 9, 11)):
    trials = []
    for bi, block in enumerate(BLOCKS):
        for scale in SCALES:
            for replicate, seed in enumerate(SEEDS):
                e_peak = e_peaks[bi]
                c_peak = c_peaks[bi]
                trials.append(
                    {
                        "task_block": block,
                        "interaction_scale": scale,
                        "replicate": replicate,
                        "seed": seed,
                        "non_geometry_invariants": {"x": "same"},
                        "information_efficiency": max(0.0, 1.0 - 0.02 * abs(scale - e_peak)),
                        "capability": max(0.0, 1.0 - 0.02 * abs(scale - c_peak)),
                    }
                )
    return trials


def test_surviving_ordered_shift():
    result = evaluate(synthetic())
    assert result["status"] == "NOT_FALSIFIED_BY_DATA"


def test_efficiency_order_failure_falsifies():
    result = evaluate(synthetic(e_peaks=(6, 10, 9)))
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["gates"]["efficiency_strict_order"] is False


def test_capability_order_failure_falsifies():
    result = evaluate(synthetic(c_peaks=(6, 10, 9)))
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["gates"]["capability_strict_order"] is False


def test_small_large_shift_floor_is_binding():
    result = evaluate(synthetic(e_peaks=(8, 9, 9), c_peaks=(8, 9, 9)))
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["gates"]["minimum_small_large_shift"] is False


def test_within_geometry_alignment_is_binding():
    result = evaluate(synthetic(e_peaks=(5, 9, 13), c_peaks=(8, 11, 14)))
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["gates"]["within_geometry_alignment"] is False


def test_boundary_median_peak_falsifies():
    result = evaluate(synthetic(e_peaks=(4, 9, 13)))
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["gates"]["median_peaks_interior"] is False


def test_invariant_drift_is_insufficient():
    trials = synthetic()
    trials[0]["non_geometry_invariants"] = {"x": "drift"}
    result = evaluate(trials)
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["reason"] == "invariant_drift"


def test_missing_cell_is_insufficient():
    trials = synthetic()
    trials = [
        t for t in trials
        if not (t["task_block"] == 13 and t["interaction_scale"] == 15)
    ]
    result = evaluate(trials)
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
