from __future__ import annotations

import math

from scale_geometry_falsifier import evaluate

SCALES = (1, 2, 4, 8, 16)
GEOMETRIES = (5, 9, 13)


def curve(x: float, vertex: float, peak: float = 0.78, curvature: float = 0.03) -> float:
    return peak - curvature * (x - vertex) ** 2


def trials(
    efficiency_vertices=(1.5, 2.2, 2.9),
    capability_vertices=(1.6, 2.3, 3.0),
    replicate_overrides=None,
):
    rows = []
    overrides = replicate_overrides or {}
    for gi, geometry in enumerate(GEOMETRIES):
        for scale in SCALES:
            x = math.log2(scale)
            for replicate in range(5):
                ev = overrides.get(("e", geometry, replicate), efficiency_vertices[gi])
                cv = overrides.get(("c", geometry, replicate), capability_vertices[gi])
                rows.append(
                    {
                        "task_block": geometry,
                        "interaction_scale": scale,
                        "replicate": replicate,
                        "information_efficiency": curve(x, ev),
                        "capability": curve(x, cv, peak=0.80, curvature=0.025),
                        "non_geometry_invariants": {"topology": "same", "compute": "same"},
                    }
                )
    return rows


def test_surviving_geometry_shift():
    verdict = evaluate(trials())
    assert verdict["status"] == "NOT_FALSIFIED_BY_DATA"
    assert all(verdict["gates"].values())


def test_wrong_efficiency_order_falsifies():
    verdict = evaluate(trials(efficiency_vertices=(1.5, 2.2, 1.9)))
    assert verdict["status"] == "FALSIFIED_BY_DATA"
    assert verdict["gates"]["efficiency_vertex_order"] is False


def test_out_of_range_vertex_falsifies():
    verdict = evaluate(trials(capability_vertices=(1.6, 2.3, 4.5)))
    assert verdict["status"] == "FALSIFIED_BY_DATA"
    assert verdict["gates"]["aggregate_vertices_interior"] is False


def test_too_small_shift_falsifies():
    verdict = evaluate(
        trials(
            efficiency_vertices=(2.0, 2.1, 2.2),
            capability_vertices=(2.0, 2.1, 2.2),
        )
    )
    assert verdict["status"] == "FALSIFIED_BY_DATA"
    assert verdict["gates"]["efficiency_small_large_shift"] is False
    assert verdict["gates"]["capability_small_large_shift"] is False


def test_replicate_direction_failure_is_detected():
    overrides = {}
    for replicate in (0, 1, 2):
        overrides[("e", 13, replicate)] = 1.2
        overrides[("c", 13, replicate)] = 1.2
    verdict = evaluate(trials(replicate_overrides=overrides))
    assert verdict["status"] == "FALSIFIED_BY_DATA"
    assert (
        verdict["gates"]["paired_efficiency_direction"] is False
        or verdict["gates"]["paired_capability_direction"] is False
    )


def test_non_geometry_invariant_drift_is_insufficient():
    rows = trials()
    rows[0]["non_geometry_invariants"] = {"topology": "changed", "compute": "same"}
    verdict = evaluate(rows)
    assert verdict == {
        "status": "INSUFFICIENT_EVIDENCE",
        "reason": "non_geometry_invariant_drift",
    }


def test_missing_geometry_scale_cell_is_insufficient():
    rows = [
        row for row in trials()
        if not (row["task_block"] == 13 and row["interaction_scale"] == 16)
    ]
    verdict = evaluate(rows)
    assert verdict == {"status": "INSUFFICIENT_EVIDENCE", "reason": "coverage"}
