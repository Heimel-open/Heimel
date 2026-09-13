#!/usr/bin/env python3
"""Frozen evaluator for SCALE-GEOMETRY-09."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean

from scale_efficiency_falsifier import quadratic_fit

SCALES = (1, 2, 4, 8, 16)
GEOMETRIES = (5, 9, 13)
REQUIRED_REPLICATES = 5
VERTEX_ALIGNMENT_TOLERANCE = 0.75
MIN_SMALL_LARGE_SHIFT = 0.25
MIN_PAIRED_SHIFT_REPLICATES = 4


def _fit_vertex(values_by_scale: dict[int, float]) -> tuple[float, float, float, float | None]:
    xs = [math.log2(scale) for scale in SCALES]
    ys = [values_by_scale[scale] for scale in SCALES]
    a, b, c = quadratic_fit(xs, ys)
    vertex = (-b / (2.0 * a)) if a < 0.0 else None
    return a, b, c, vertex


def evaluate(trials: list[dict[str, object]]) -> dict[str, object]:
    if not trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no_trials"}

    grouped: dict[tuple[int, int], list[dict[str, object]]] = defaultdict(list)
    invariant_fingerprints = set()

    for trial in trials:
        try:
            geometry = int(trial["task_block"])
            scale = int(trial["interaction_scale"])
            replicate = int(trial["replicate"])
            efficiency = float(trial["information_efficiency"])
            capability = float(trial["capability"])
            invariants = tuple(sorted(dict(trial["non_geometry_invariants"]).items()))
        except (KeyError, TypeError, ValueError):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "malformed_trial"}

        if geometry not in GEOMETRIES or scale not in SCALES or replicate < 0:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "unexpected_geometry_scale_or_replicate"}
        if not all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in (efficiency, capability)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invalid_score"}

        grouped[(geometry, scale)].append(trial)
        invariant_fingerprints.add(invariants)

    if len(invariant_fingerprints) != 1:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "non_geometry_invariant_drift"}

    expected = {(geometry, scale) for geometry in GEOMETRIES for scale in SCALES}
    if set(grouped) != expected:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "coverage"}

    for key in expected:
        bucket = grouped[key]
        if len(bucket) != REQUIRED_REPLICATES:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_coverage"}
        reps = sorted(int(t["replicate"]) for t in bucket)
        if reps != list(range(REQUIRED_REPLICATES)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_pairing"}

    aggregate: dict[int, dict[str, object]] = {}
    for geometry in GEOMETRIES:
        efficiency_by_scale = {
            scale: mean(float(t["information_efficiency"]) for t in grouped[(geometry, scale)])
            for scale in SCALES
        }
        capability_by_scale = {
            scale: mean(float(t["capability"]) for t in grouped[(geometry, scale)])
            for scale in SCALES
        }
        try:
            ea, eb, ec, ev = _fit_vertex(efficiency_by_scale)
            ca, cb, cc, cv = _fit_vertex(capability_by_scale)
        except ValueError:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "quadratic_fit_failed"}
        aggregate[geometry] = {
            "efficiency_by_scale": efficiency_by_scale,
            "capability_by_scale": capability_by_scale,
            "efficiency_quadratic": {"a": ea, "b": eb, "c": ec},
            "capability_quadratic": {"a": ca, "b": cb, "c": cc},
            "efficiency_vertex_log2": ev,
            "capability_vertex_log2": cv,
            "efficiency_vertex_scale": (2.0**ev) if ev is not None else None,
            "capability_vertex_scale": (2.0**cv) if cv is not None else None,
        }

    efficiency_vertices = [aggregate[g]["efficiency_vertex_log2"] for g in GEOMETRIES]
    capability_vertices = [aggregate[g]["capability_vertex_log2"] for g in GEOMETRIES]

    aggregate_concave = all(
        float(aggregate[g][metric]["a"]) < 0.0
        for g in GEOMETRIES
        for metric in ("efficiency_quadratic", "capability_quadratic")
    )
    aggregate_interior = all(
        vertex is not None and 0.0 < float(vertex) < 4.0
        for vertex in efficiency_vertices + capability_vertices
    )
    vertex_alignment = all(
        aggregate[g]["efficiency_vertex_log2"] is not None
        and aggregate[g]["capability_vertex_log2"] is not None
        and abs(
            float(aggregate[g]["efficiency_vertex_log2"])
            - float(aggregate[g]["capability_vertex_log2"])
        ) <= VERTEX_ALIGNMENT_TOLERANCE
        for g in GEOMETRIES
    )

    efficiency_order = all(
        efficiency_vertices[i] is not None
        and efficiency_vertices[i + 1] is not None
        and float(efficiency_vertices[i]) < float(efficiency_vertices[i + 1])
        for i in range(len(GEOMETRIES) - 1)
    )
    capability_order = all(
        capability_vertices[i] is not None
        and capability_vertices[i + 1] is not None
        and float(capability_vertices[i]) < float(capability_vertices[i + 1])
        for i in range(len(GEOMETRIES) - 1)
    )

    efficiency_shift = (
        float(efficiency_vertices[-1]) - float(efficiency_vertices[0])
        if efficiency_vertices[0] is not None and efficiency_vertices[-1] is not None
        else None
    )
    capability_shift = (
        float(capability_vertices[-1]) - float(capability_vertices[0])
        if capability_vertices[0] is not None and capability_vertices[-1] is not None
        else None
    )

    paired_efficiency_shifts = 0
    paired_capability_shifts = 0
    replicate_vertices = []
    for replicate in range(REQUIRED_REPLICATES):
        record: dict[str, object] = {"replicate": replicate}
        for metric, counter_name in (
            ("information_efficiency", "efficiency"),
            ("capability", "capability"),
        ):
            vertices: dict[int, float | None] = {}
            for geometry in (GEOMETRIES[0], GEOMETRIES[-1]):
                values = {
                    scale: float(
                        next(
                            t for t in grouped[(geometry, scale)]
                            if int(t["replicate"]) == replicate
                        )[metric]
                    )
                    for scale in SCALES
                }
                try:
                    _, _, _, vertex = _fit_vertex(values)
                except ValueError:
                    vertex = None
                vertices[geometry] = vertex
            positive = (
                vertices[GEOMETRIES[0]] is not None
                and vertices[GEOMETRIES[-1]] is not None
                and 0.0 < float(vertices[GEOMETRIES[0]]) < 4.0
                and 0.0 < float(vertices[GEOMETRIES[-1]]) < 4.0
                and float(vertices[GEOMETRIES[-1]]) > float(vertices[GEOMETRIES[0]])
            )
            record[f"{counter_name}_small_vertex_log2"] = vertices[GEOMETRIES[0]]
            record[f"{counter_name}_large_vertex_log2"] = vertices[GEOMETRIES[-1]]
            record[f"{counter_name}_positive_shift"] = positive
            if counter_name == "efficiency":
                paired_efficiency_shifts += int(positive)
            else:
                paired_capability_shifts += int(positive)
        replicate_vertices.append(record)

    gates = {
        "aggregate_concave": aggregate_concave,
        "aggregate_vertices_interior": aggregate_interior,
        "within_geometry_vertex_alignment": vertex_alignment,
        "efficiency_vertex_order": efficiency_order,
        "capability_vertex_order": capability_order,
        "efficiency_small_large_shift": efficiency_shift is not None and efficiency_shift >= MIN_SMALL_LARGE_SHIFT,
        "capability_small_large_shift": capability_shift is not None and capability_shift >= MIN_SMALL_LARGE_SHIFT,
        "paired_efficiency_direction": paired_efficiency_shifts >= MIN_PAIRED_SHIFT_REPLICATES,
        "paired_capability_direction": paired_capability_shifts >= MIN_PAIRED_SHIFT_REPLICATES,
    }

    return {
        "status": "NOT_FALSIFIED_BY_DATA" if all(gates.values()) else "FALSIFIED_BY_DATA",
        "aggregate": aggregate,
        "efficiency_small_large_shift_log2": efficiency_shift,
        "capability_small_large_shift_log2": capability_shift,
        "paired_efficiency_positive_shifts": paired_efficiency_shifts,
        "paired_capability_positive_shifts": paired_capability_shifts,
        "replicate_vertices": replicate_vertices,
        "gates": gates,
    }
