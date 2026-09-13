#!/usr/bin/env python3
"""Frozen evaluator for SCALE-RATIO-15."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean, median

BLOCKS = (6, 8, 10, 12, 14)
SCALES = tuple(range(4, 16))
CONDITIONS = ("reflected", "self_padded")
REPLICATES = 5
MAX_MEDIAN_ERROR = 1.0
MAX_REPLICATE_ERROR = 2.0
MIN_REPLICATES_NEAR = 4
MAX_BOUNDARY_MEDIAN_DELTA = 1.0
MIN_BOUNDARY_ROBUST_BLOCKS = 4


def _peak(scores: dict[int, float]) -> float:
    maximum = max(scores.values())
    tied = [scale for scale in SCALES if scores[scale] == maximum]
    return mean(tied)


def evaluate(trials: list[dict[str, object]]) -> dict[str, object]:
    if not trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no_trials"}

    by_condition_cell: dict[tuple[str, int, int], list[dict[str, object]]] = defaultdict(list)
    condition_invariants: dict[str, set[tuple[tuple[str, object], ...]]] = defaultdict(set)
    seed_map: dict[tuple[str, int], set[int]] = defaultdict(set)

    for trial in trials:
        try:
            condition = str(trial["boundary_condition"])
            block = int(trial["task_block"])
            scale = int(trial["interaction_scale"])
            replicate = int(trial["replicate"])
            seed = int(trial["seed"])
            capability = float(trial["capability"])
            efficiency = float(trial["information_efficiency"])
            invariants = tuple(sorted(dict(trial["condition_invariants"]).items()))
        except (KeyError, TypeError, ValueError):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "malformed_trial"}

        if condition not in CONDITIONS or block not in BLOCKS or scale not in SCALES:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "unexpected_condition"}
        if not 0 <= replicate < REPLICATES:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "unexpected_replicate"}
        if not all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in (capability, efficiency)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invalid_score"}

        by_condition_cell[(condition, block, scale)].append(trial)
        condition_invariants[condition].add(invariants)
        seed_map[(condition, replicate)].add(seed)

    if any(len(condition_invariants[c]) != 1 for c in CONDITIONS):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invariant_drift"}
    for replicate in range(REPLICATES):
        seeds = [seed_map[(condition, replicate)] for condition in CONDITIONS]
        if any(len(s) != 1 for s in seeds):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "seed_pairing"}
        if next(iter(seeds[0])) != next(iter(seeds[1])):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "cross_condition_seed_mismatch"}

    expected = {(c, b, s) for c in CONDITIONS for b in BLOCKS for s in SCALES}
    if set(by_condition_cell) != expected:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "condition_coverage"}
    for cell in expected:
        rows = by_condition_cell[cell]
        if len(rows) != REPLICATES:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_coverage"}
        if sorted(int(r["replicate"]) for r in rows) != list(range(REPLICATES)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_pairing"}

    replicate_peaks = {
        metric: {condition: {} for condition in CONDITIONS}
        for metric in ("capability", "information_efficiency")
    }
    median_peaks = {
        metric: {condition: {} for condition in CONDITIONS}
        for metric in ("capability", "information_efficiency")
    }

    for metric in replicate_peaks:
        for condition in CONDITIONS:
            for block in BLOCKS:
                peaks = []
                for replicate in range(REPLICATES):
                    scores = {
                        scale: float(next(
                            row for row in by_condition_cell[(condition, block, scale)]
                            if int(row["replicate"]) == replicate
                        )[metric])
                        for scale in SCALES
                    }
                    peaks.append(_peak(scores))
                replicate_peaks[metric][condition][block] = peaks
                median_peaks[metric][condition][block] = median(peaks)

    gates = {}
    condition_diagnostics = {}
    all_pass = True
    for condition in CONDITIONS:
        capability = median_peaks["capability"][condition]
        ordered = all(capability[a] < capability[b] for a, b in zip(BLOCKS, BLOCKS[1:]))
        median_errors = {block: abs(capability[block] - block) for block in BLOCKS}
        every_median_near = all(error <= MAX_MEDIAN_ERROR for error in median_errors.values())
        mae = mean(median_errors.values())
        replicate_near_counts = {
            block: sum(abs(peak - block) <= MAX_REPLICATE_ERROR for peak in replicate_peaks["capability"][condition][block])
            for block in BLOCKS
        }
        every_block_replicated = all(count >= MIN_REPLICATES_NEAR for count in replicate_near_counts.values())
        condition_pass = ordered and every_median_near and mae <= MAX_MEDIAN_ERROR and every_block_replicated
        gates[f"{condition}_strict_order"] = ordered
        gates[f"{condition}_all_medians_within_one"] = every_median_near
        gates[f"{condition}_median_absolute_error_le_one"] = mae <= MAX_MEDIAN_ERROR
        gates[f"{condition}_replicate_support"] = every_block_replicated
        condition_diagnostics[condition] = {
            "capability_median_errors": median_errors,
            "capability_median_absolute_error": mae,
            "replicate_near_counts": replicate_near_counts,
        }
        all_pass = all_pass and condition_pass

    boundary_deltas = {
        block: abs(
            median_peaks["capability"]["reflected"][block]
            - median_peaks["capability"]["self_padded"][block]
        )
        for block in BLOCKS
    }
    robust_blocks = sum(delta <= MAX_BOUNDARY_MEDIAN_DELTA for delta in boundary_deltas.values())
    boundary_robust = robust_blocks >= MIN_BOUNDARY_ROBUST_BLOCKS
    gates["boundary_robustness"] = boundary_robust
    all_pass = all_pass and boundary_robust

    normalized_ratios = {
        metric: {
            condition: {
                block: median_peaks[metric][condition][block] / block
                for block in BLOCKS
            }
            for condition in CONDITIONS
        }
        for metric in median_peaks
    }

    return {
        "status": "NOT_FALSIFIED_BY_DATA" if all_pass else "FALSIFIED_BY_DATA",
        "median_peaks": median_peaks,
        "replicate_peaks": replicate_peaks,
        "normalized_peak_to_task_ratios": normalized_ratios,
        "condition_diagnostics": condition_diagnostics,
        "boundary_median_peak_deltas": boundary_deltas,
        "boundary_robust_blocks": robust_blocks,
        "gates": gates,
    }
