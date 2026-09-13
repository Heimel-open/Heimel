from scale_boundary_dynamics_falsifier import evaluate

BLOCKS = (5, 9, 13)
SCALES = tuple(range(4, 16))
SEEDS = (1, 2, 3, 4, 5)


def synthetic(ref_peaks=(5, 9, 13), self_peaks=(8, 9, 13)):
    rows = []
    for condition, peaks in (
        ("reflected", ref_peaks),
        ("self_padded", self_peaks),
    ):
        for bi, block in enumerate(BLOCKS):
            peak = peaks[bi]
            for scale in SCALES:
                for replicate, seed in enumerate(SEEDS):
                    rows.append(
                        {
                            "boundary_condition": condition,
                            "task_block": block,
                            "interaction_scale": scale,
                            "replicate": replicate,
                            "seed": seed,
                            "condition_invariants": {
                                "topology": condition,
                                "x": "fixed",
                            },
                            "information_efficiency": max(
                                0.0, 1.0 - 0.02 * abs(scale - peak)
                            ),
                            "capability": max(
                                0.0, 1.0 - 0.02 * abs(scale - peak)
                            ),
                        }
                    )
    return rows


def test_coherent_primary_shift_survives():
    result = evaluate(synthetic())
    assert result["status"] == "NOT_FALSIFIED_BY_DATA"
    assert result["primary"]["median_shift"] == 3
    assert result["primary"]["directional_replicates"] == 5


def test_small_shift_falsifies():
    result = evaluate(synthetic(self_peaks=(6, 9, 13)))
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert result["gates"]["material_median_shift"] is False


def test_no_shift_falsifies():
    result = evaluate(synthetic(self_peaks=(5, 9, 13)))
    assert result["status"] == "FALSIFIED_BY_DATA"


def test_condition_relation_failure_is_insufficient():
    result = evaluate(synthetic(self_peaks=(10, 9, 13)))
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
    assert result["reason"] == "condition_geometry_relation_failed"


def test_missing_condition_is_insufficient():
    rows = [
        row
        for row in synthetic()
        if row["boundary_condition"] == "reflected"
    ]
    result = evaluate(rows)
    assert result["status"] == "INSUFFICIENT_EVIDENCE"


def test_invariant_drift_is_insufficient():
    rows = synthetic()
    rows[0]["condition_invariants"] = {"topology": "drift", "x": "fixed"}
    result = evaluate(rows)
    assert result["status"] == "INSUFFICIENT_EVIDENCE"
