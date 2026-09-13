#!/usr/bin/env python3
"""Frozen evaluator for SCALE-EFFICIENCY-08."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean

SCALES = (1, 2, 4, 8, 16)
REQUIRED_REPLICATES = 5
VERTEX_TOLERANCE_LOG2 = 0.75
MIN_SPEARMAN = 0.80
MIN_INTERIOR_WINNERS = 4


def _solve3(matrix: list[list[float]], vector: list[float]) -> tuple[float, float, float]:
    a = [row[:] + [rhs] for row, rhs in zip(matrix, vector)]
    for col in range(3):
        pivot = max(range(col, 3), key=lambda r: abs(a[r][col]))
        if abs(a[pivot][col]) < 1e-12:
            raise ValueError("singular quadratic fit")
        a[col], a[pivot] = a[pivot], a[col]
        div = a[col][col]
        a[col] = [v / div for v in a[col]]
        for row in range(3):
            if row == col:
                continue
            factor = a[row][col]
            a[row] = [x - factor * y for x, y in zip(a[row], a[col])]
    return a[0][3], a[1][3], a[2][3]


def quadratic_fit(xs: list[float], ys: list[float]) -> tuple[float, float, float]:
    if len(xs) != len(ys) or len(xs) < 3:
        raise ValueError("quadratic fit requires paired observations")
    matrix = [
        [sum(x**4 for x in xs), sum(x**3 for x in xs), sum(x*x for x in xs)],
        [sum(x**3 for x in xs), sum(x*x for x in xs), sum(xs)],
        [sum(x*x for x in xs), sum(xs), float(len(xs))],
    ]
    vector = [
        sum((x*x) * y for x, y in zip(xs, ys)),
        sum(x * y for x, y in zip(xs, ys)),
        sum(ys),
    ]
    return _solve3(matrix, vector)


def _ranks(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = 0.5 * ((i + 1) + j)
        for k in range(i, j):
            ranks[order[k]] = rank
        i = j
    return ranks


def spearman(a: list[float], b: list[float]) -> float:
    ra, rb = _ranks(a), _ranks(b)
    ma, mb = mean(ra), mean(rb)
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    db = math.sqrt(sum((x - mb) ** 2 for x in rb))
    if da <= 0.0 or db <= 0.0:
        return 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / (da * db)


def evaluate(trials: list[dict[str, object]]) -> dict[str, object]:
    if not trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no_trials"}

    by_scale: dict[int, list[dict[str, object]]] = defaultdict(list)
    invariant_fingerprints = set()
    for trial in trials:
        try:
            scale = int(trial["interaction_scale"])
            replicate = int(trial["replicate"])
            efficiency = float(trial["information_efficiency"])
            capability = float(trial["capability"])
            invariants = tuple(sorted(dict(trial["invariants"]).items()))
        except (KeyError, TypeError, ValueError):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "malformed_trial"}
        if scale not in SCALES or replicate < 0:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "unexpected_scale_or_replicate"}
        if not all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in (efficiency, capability)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invalid_score"}
        by_scale[scale].append(trial)
        invariant_fingerprints.add(invariants)

    if len(invariant_fingerprints) != 1:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invariant_drift"}
    if set(by_scale) != set(SCALES) or any(len(by_scale[s]) != REQUIRED_REPLICATES for s in SCALES):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_coverage"}

    for scale in SCALES:
        reps = sorted(int(t["replicate"]) for t in by_scale[scale])
        if reps != list(range(REQUIRED_REPLICATES)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_pairing"}

    efficiency_by_scale = {s: mean(float(t["information_efficiency"]) for t in by_scale[s]) for s in SCALES}
    capability_by_scale = {s: mean(float(t["capability"]) for t in by_scale[s]) for s in SCALES}
    xs = [math.log2(s) for s in SCALES]
    eys = [efficiency_by_scale[s] for s in SCALES]
    cys = [capability_by_scale[s] for s in SCALES]

    try:
        ea, eb, ec = quadratic_fit(xs, eys)
        ca, cb, cc = quadratic_fit(xs, cys)
    except ValueError:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "quadratic_fit_failed"}

    e_vertex = (-eb / (2.0 * ea)) if ea < 0.0 else None
    c_vertex = (-cb / (2.0 * ca)) if ca < 0.0 else None
    rho = spearman(eys, cys)

    interior_winners = 0
    for replicate in range(REQUIRED_REPLICATES):
        scores = {
            s: float(next(t for t in by_scale[s] if int(t["replicate"]) == replicate)["information_efficiency"])
            for s in SCALES
        }
        if max(scores[s] for s in (2, 4, 8)) > max(scores[1], scores[16]):
            interior_winners += 1

    gates = {
        "efficiency_concave": ea < 0.0,
        "capability_concave": ca < 0.0,
        "efficiency_vertex_interior": e_vertex is not None and 0.0 < e_vertex < 4.0,
        "capability_vertex_interior": c_vertex is not None and 0.0 < c_vertex < 4.0,
        "vertex_alignment": e_vertex is not None and c_vertex is not None and abs(e_vertex - c_vertex) <= VERTEX_TOLERANCE_LOG2,
        "rank_alignment": rho >= MIN_SPEARMAN,
        "replicate_interior_winners": interior_winners >= MIN_INTERIOR_WINNERS,
    }
    status = "NOT_FALSIFIED_BY_DATA" if all(gates.values()) else "FALSIFIED_BY_DATA"

    return {
        "status": status,
        "efficiency_by_scale": efficiency_by_scale,
        "capability_by_scale": capability_by_scale,
        "efficiency_quadratic": {"a": ea, "b": eb, "c": ec},
        "capability_quadratic": {"a": ca, "b": cb, "c": cc},
        "efficiency_vertex_log2": e_vertex,
        "capability_vertex_log2": c_vertex,
        "efficiency_vertex_scale": (2.0**e_vertex) if e_vertex is not None else None,
        "capability_vertex_scale": (2.0**c_vertex) if c_vertex is not None else None,
        "vertex_distance_log2": abs(e_vertex - c_vertex) if e_vertex is not None and c_vertex is not None else None,
        "spearman": rho,
        "interior_efficiency_winners": interior_winners,
        "gates": gates,
    }
