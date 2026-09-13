from scale_correlation_falsifier import evaluate

BLOCKS = (3, 6)
CORRS = (8, 11, 14)
SCALES = tuple(range(4, 16))
CONDS = ("reflected", "self_padded")
SEEDS = (1, 2, 3, 4, 5)


def synthetic(offset=0, follow_block=False):
    rows = []
    for condition in CONDS:
        for block in BLOCKS:
            for corr in CORRS:
                peak = block if follow_block else corr + offset
                for scale in SCALES:
                    for replicate, seed in enumerate(SEEDS):
                        rows.append({
                            "boundary_condition": condition,
                            "nominal_block": block,
                            "correlation_length": corr,
                            "interaction_scale": scale,
                            "replicate": replicate,
                            "seed": seed,
                            "condition_invariants": {"condition": condition},
                            "capability": max(0.0, 1.0 - 0.02 * abs(scale - peak)),
                        })
    return rows


def test_correlation_tracking_survives():
    assert evaluate(synthetic())["status"] == "NOT_FALSIFIED_BY_DATA"


def test_tracking_nominal_block_falsifies():
    assert evaluate(synthetic(follow_block=True))["status"] == "FALSIFIED_BY_DATA"


def test_too_far_from_correlation_falsifies():
    assert evaluate(synthetic(offset=-3))["status"] == "FALSIFIED_BY_DATA"


def test_missing_condition_is_insufficient():
    rows = [r for r in synthetic() if r["boundary_condition"] == "reflected"]
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"


def test_invariant_drift_is_insufficient():
    rows = synthetic()
    rows[0]["condition_invariants"] = {"condition": "drift"}
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"
