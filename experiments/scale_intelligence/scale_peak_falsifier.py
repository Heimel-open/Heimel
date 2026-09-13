#!/usr/bin/env python3
"""Frozen nonparametric evaluator for SCALE-PEAK-10."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean, median

TASK_BLOCKS = (5, 9, 13)
SCALES = tuple(range(4, 16))
REQUIRED_REPLICATES = 5
MIN_SMALL_LARGE_SHIFT = 2.0
MAX_WITHIN_GEOMETRY_DISTANCE = 2.0
MIN_PAIRED_OUTWARD = 4


def _peak_location(scores: dict[int, float]) -> float:
    maximum = max(scores.values())
    tied = [scale for scale in SCALES if scores[scale] == maximum]
    return mean(tied)


def evaluate(trials: list[dict[str, object]]) -> dict[str, object]:
    if not trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no_trials"}

    by_cell: dict[tuple[int, int], list[dict[str, object]]] = defaultdict(list)
    invariant_fingerprints = set()
    replicate_seeds: dict[int, set[int]] = defaultdict(set)

    for trial in trials:
        try:
            block = int(trial["task_block"])
            scale = int(trial["interaction_scale"])
            replicate = int(trial["replicate"])
            seed = int(trial["seed"])
            efficiency = float(trial["information_efficiency"])
            capability = float(trial["capability"])
            invariants = tuple(sorted(dict(trial["non_geometry_invariants"]).items()))
        except (KeyError, TypeError, ValueError):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "malformed_trial"}

        if block not in TASK_BLOCKS or scale not in SCALES or not 0 <= replicate < REQUIRED_REPLICATES:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "unexpected_condition"}
        if not all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in (efficiency, capability)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invalid_score"}

        by_cell[(block, scale)].append(trial)
        invariant_fingerprints.add(invariants)
        replicate_seeds[replicate].add(seed)

    if len(invariant_fingerprints) != 1:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invariant_drift"}
    if any(len(replicate_seeds[r]) != 1 for r in range(REQUIRED_REPLICATES)):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "seed_pairing"}

    expected_cells = {(b, s) for b in TASK_BLOCKS for s in SCALES}
    if set(by_cell) != expected_cells:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "condition_coverage"}
    for cell in expected_cells:
        rows = by_cell[cell]
        if len(rows) != REQUIRED_REPLICATES:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_coverage"}
        reps = sorted(int(row["replicate"]) for row in rows)
        if reps != list(range(REQUIRED_REPLICATES)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_pairing"}

    aggregate = {
        block: {
            scale: {
                "information_efficiency": mean(float(t["information_efficiency"]) for t in by_cell[(block, scale)]),
                "capability": mean(float(t["capability"]) for t in by_cell[(block, scale)]),
            }
            for scale in SCALES
        }
        for block in TASK_BLOCKS
    }

    replicate_peaks = {"information_efficiency": {}, "capability": {}}
    median_peaks = {"information_efficiency": {}, "capability": {}}

    for metric in ("information_efficiency", "capability"):
        for block in TASK_BLOCKS:
            peaks = []
            for replicate in range(REQUIRED_REPLICATES):
                scores = {
                    scale: float(next(
                        t for t in by_cell[(block, scale)]
                        if int(t["replicate"]) == replicate
                    )[metric])
                    for scale in SCALES
                }
                peaks.append(_peak_location(scores))
            replicate_peaks[metric][block] = peaks
            median_peaks[metric][block] = median(peaks)

    e = median_peaks["information_efficiency"]
    c = median_peaks["capability"]
    e_outward = sum(
        replicate_peaks["information_efficiency"][13][r]
        > replicate_peaks["information_efficiency"][5][r]
        for r in range(REQUIRED_REPLICATES)
    )
    c_outward = sum(
        replicate_peaks["capability"][13][r]
        > replicate_peaks["capability"][5][r]
        for r in range(REQUIRED_REPLICATES)
    )

    gates = {
        "median_peaks_interior": all(
            SCALES[0] < peak < SCALES[-1]
            for metric in median_peaks.values()
            for peak in metric.values()
        ),
        "efficiency_strict_order": e[5] < e[9] < e[13],
        "capability_strict_order": c[5] < c[9] < c[13],
        "minimum_small_large_shift": (
            e[13] - e[5] >= MIN_SMALL_LARGE_SHIFT
            and c[13] - c[5] >= MIN_SMALL_LARGE_SHIFT
        ),
        "within_geometry_alignment": all(
            abs(e[block] - c[block]) <= MAX_WITHIN_GEOMETRY_DISTANCE
            for block in TASK_BLOCKS
        ),
        "paired_efficiency_outward": e_outward >= MIN_PAIRED_OUTWARD,
        "paired_capability_outward": c_outward >= MIN_PAIRED_OUTWARD,
    }

    return {
        "status": "NOT_FALSIFIED_BY_DATA" if all(gates.values()) else "FALSIFIED_BY_DATA",
        "aggregate_by_geometry_scale": aggregate,
        "replicate_peaks": replicate_peaks,
        "median_peaks": median_peaks,
        "paired_outward_counts": {
            "information_efficiency": e_outward,
            "capability": c_outward,
        },
        "gates": gates,
    }
