from scale_efficiency_falsifier import evaluate

SCALES = (1, 2, 4, 8, 16)


def trials(eff, cap, invariants=None):
    invariants = invariants or {"frozen": "yes"}
    out = []
    for replicate in range(5):
        for scale in SCALES:
            out.append(
                {
                    "interaction_scale": scale,
                    "replicate": replicate,
                    "seed": 22022 + replicate,
                    "invariants": dict(invariants),
                    "information_efficiency": eff[scale] - 0.001 * replicate,
                    "capability": cap[scale] - 0.001 * replicate,
                }
            )
    return out


def good_curves():
    eff = {1: 0.48, 2: 0.59, 4: 0.68, 8: 0.73, 16: 0.68}
    cap = {1: 0.64, 2: 0.68, 4: 0.74, 8: 0.80, 16: 0.74}
    return eff, cap


def test_survives_aligned_interior_optima():
    eff, cap = good_curves()
    assert evaluate(trials(eff, cap))["status"] == "NOT_FALSIFIED_BY_DATA"


def test_monotonic_efficiency_falsifies():
    _, cap = good_curves()
    eff = {1: 0.40, 2: 0.50, 4: 0.60, 8: 0.70, 16: 0.80}
    assert evaluate(trials(eff, cap))["status"] == "FALSIFIED_BY_DATA"


def test_far_apart_vertices_falsify():
    eff = {1: 0.45, 2: 0.65, 4: 0.75, 8: 0.68, 16: 0.50}
    cap = {1: 0.50, 2: 0.55, 4: 0.62, 8: 0.74, 16: 0.72}
    result = evaluate(trials(eff, cap))
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert not result["gates"]["vertex_alignment"]


def test_rank_misalignment_falsifies():
    eff = {1: 0.48, 2: 0.60, 4: 0.70, 8: 0.73, 16: 0.68}
    cap = {1: 0.68, 2: 0.74, 4: 0.64, 8: 0.80, 16: 0.70}
    result = evaluate(trials(eff, cap))
    assert result["status"] == "FALSIFIED_BY_DATA"
    assert not result["gates"]["rank_alignment"]


def test_invariant_drift_is_insufficient():
    eff, cap = good_curves()
    data = trials(eff, cap)
    data[-1]["invariants"] = {"frozen": "no"}
    assert evaluate(data)["status"] == "INSUFFICIENT_EVIDENCE"


def test_missing_replicate_is_insufficient():
    eff, cap = good_curves()
    data = trials(eff, cap)
    data.pop()
    assert evaluate(data)["status"] == "INSUFFICIENT_EVIDENCE"


def test_invalid_score_is_insufficient():
    eff, cap = good_curves()
    data = trials(eff, cap)
    data[0]["information_efficiency"] = 1.2
    assert evaluate(data)["status"] == "INSUFFICIENT_EVIDENCE"
