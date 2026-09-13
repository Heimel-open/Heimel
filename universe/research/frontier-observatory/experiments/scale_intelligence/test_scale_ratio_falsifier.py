from scale_ratio_falsifier import BLOCKS, SCALES, evaluate

SEEDS = (1, 2, 3, 4, 5)


def synthetic(reflected=(6, 8, 10, 12, 14), self_padded=(6, 8, 10, 12, 14)):
    rows = []
    for condition, peaks in (("reflected", reflected), ("self_padded", self_padded)):
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
                            "condition_invariants": {"condition": condition},
                            "information_efficiency": max(0.0, 1.0 - 0.01 * abs(scale - peak)),
                            "capability": max(0.0, 1.0 - 0.02 * abs(scale - peak)),
                        }
                    )
    return rows


def test_exact_matching_survives():
    result = evaluate(synthetic())
    assert result["status"] == "NOT_FALSIFIED_BY_DATA"
    assert result["boundary_robust_blocks"] == 5


def test_one_unit_offsets_survive():
    result = evaluate(synthetic(reflected=(5, 7, 9, 11, 13), self_padded=(6, 8, 10, 12, 14)))
    assert result["status"] == "NOT_FALSIFIED_BY_DATA"


def test_wrong_scale_falsifies():
    result = evaluate(synthetic(reflected=(6, 8, 10, 12, 14), self_padded=(6, 8, 10, 10, 10)))
    assert result["status"] == "FALSIFIED_BY_DATA"


def test_boundary_nonrobust_falsifies():
    result = evaluate(synthetic(reflected=(6, 8, 10, 12, 14), self_padded=(8, 10, 12, 14, 15)))
    assert result["status"] == "FALSIFIED_BY_DATA"


def test_missing_condition_is_insufficient():
    rows = [r for r in synthetic() if r["boundary_condition"] == "reflected"]
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"


def test_invariant_drift_is_insufficient():
    rows = synthetic()
    rows[0]["condition_invariants"] = {"condition": "drift"}
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"
