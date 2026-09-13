from scale_decoupling_falsifier import evaluate

BLOCKS = (5, 9, 13)
SCALES = tuple(range(4, 16))
SEEDS = (1, 2, 3, 4, 5)


def synthetic(e_ref=(5, 9, 13), e_self=(5, 5, 6), c_ref=(5, 9, 13), c_self=(5, 9, 13)):
    rows = []
    for condition, ep, cp in (
        ("reflected", e_ref, c_ref),
        ("self_padded", e_self, c_self),
    ):
        for bi, block in enumerate(BLOCKS):
            for scale in SCALES:
                for replicate, seed in enumerate(SEEDS):
                    rows.append({
                        "boundary_condition": condition,
                        "task_block": block,
                        "interaction_scale": scale,
                        "replicate": replicate,
                        "seed": seed,
                        "condition_invariants": {"condition": condition},
                        "information_efficiency": max(0.0, 1.0 - 0.02 * abs(scale - ep[bi])),
                        "capability": max(0.0, 1.0 - 0.02 * abs(scale - cp[bi])),
                    })
    return rows


def test_decoupling_falsifies_necessity():
    r = evaluate(synthetic())
    assert r["status"] == "FALSIFIED_BY_DATA"
    assert 9 in r["falsifying_blocks"]
    assert 13 in r["falsifying_blocks"]


def test_no_perturbation_is_insufficient():
    r = evaluate(synthetic(e_self=(5, 9, 13)))
    assert r["status"] == "INSUFFICIENT_EVIDENCE"


def test_capability_moves_with_efficiency_does_not_falsify():
    r = evaluate(synthetic(e_self=(5, 5, 6), c_self=(5, 6, 9)))
    assert r["status"] == "NOT_FALSIFIED_BY_DATA"


def test_broken_capability_order_is_insufficient():
    r = evaluate(synthetic(c_self=(5, 13, 9)))
    assert r["status"] == "INSUFFICIENT_EVIDENCE"


def test_missing_condition_is_insufficient():
    rows = [x for x in synthetic() if x["boundary_condition"] == "reflected"]
    assert evaluate(rows)["status"] == "INSUFFICIENT_EVIDENCE"
