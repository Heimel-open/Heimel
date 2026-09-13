#!/usr/bin/env python3
"""Frozen evaluator for SCALE-CORRELATION-16."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean, median

BLOCKS = (3, 6)
CORRELATION_LENGTHS = (8, 11, 14)
SCALES = tuple(range(4, 16))
CONDITIONS = ("reflected", "self_padded")
REPLICATES = 5
MAX_CORRELATION_ERROR = 2.0
MAX_BLOCK_DELTA_AT_FIXED_L = 1.0
MIN_REPLICATES_NEAR = 4
MIN_CLOSER_MARGIN = 2.0
MIN_CLOSER_CELLS = 10
MAX_BOUNDARY_DELTA = 1.0
MIN_BOUNDARY_ROBUST_CELLS = 5


def _peak(scores: dict[int, float]) -> float:
    maximum = max(scores.values())
    tied = [scale for scale in SCALES if scores[scale] == maximum]
    return mean(tied)


def evaluate(trials: list[dict[str, object]]) -> dict[str, object]:
    if not trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no_trials"}

    by_cell = defaultdict(list)
    invariant_sets = defaultdict(set)
    seed_map = defaultdict(set)

    for trial in trials:
        try:
            condition = str(trial["boundary_condition"])
            block = int(trial["nominal_block"])
            corr = int(trial["correlation_length"])
            scale = int(trial["interaction_scale"])
            replicate = int(trial["replicate"])
            seed = int(trial["seed"])
            capability = float(trial["capability"])
            invariants = tuple(sorted(dict(trial["condition_invariants"]).items()))
        except (KeyError, TypeError, ValueError):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "malformed_trial"}

        if (
            condition not in CONDITIONS
            or block not in BLOCKS
            or corr not in CORRELATION_LENGTHS
            or scale not in SCALES
            or not 0 <= replicate < REPLICATES
        ):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "unexpected_condition"}
        if not math.isfinite(capability) or not 0.0 <= capability <= 1.0:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invalid_capability"}

        by_cell[(condition, block, corr, scale)].append(trial)
        invariant_sets[condition].add(invariants)
        seed_map[(condition, replicate)].add(seed)

    if any(len(invariant_sets[c]) != 1 for c in CONDITIONS):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invariant_drift"}

    for replicate in range(REPLICATES):
        seeds = [seed_map[(c, replicate)] for c in CONDITIONS]
        if any(len(s) != 1 for s in seeds):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "seed_pairing"}
        if len({next(iter(s)) for s in seeds}) != 1:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "cross_condition_seed_mismatch"}

    expected = {
        (c, b, l, s)
        for c in CONDITIONS
        for b in BLOCKS
        for l in CORRELATION_LENGTHS
        for s in SCALES
    }
    if set(by_cell) != expected:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "condition_coverage"}

    for cell in expected:
        rows = by_cell[cell]
        if len(rows) != REPLICATES:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_coverage"}
        if sorted(int(r["replicate"]) for r in rows) != list(range(REPLICATES)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_pairing"}

    replicate_peaks = {
        condition: {block: {corr: [] for corr in CORRELATION_LENGTHS} for block in BLOCKS}
        for condition in CONDITIONS
    }
    median_peaks = {
        condition: {block: {} for block in BLOCKS}
        for condition in CONDITIONS
    }

    for condition in CONDITIONS:
        for block in BLOCKS:
            for corr in CORRELATION_LENGTHS:
                peaks = []
                for replicate in range(REPLICATES):
                    scores = {
                        scale: float(
                            next(
                                row
                                for row in by_cell[(condition, block, corr, scale)]
                                if int(row["replicate"]) == replicate
                            )["capability"]
                        )
                        for scale in SCALES
                    }
                    peaks.append(_peak(scores))
                replicate_peaks[condition][block][corr] = peaks
                median_peaks[condition][block][corr] = median(peaks)

    gates = {}
    all_pass = True

    for condition in CONDITIONS:
        for block in BLOCKS:
            p = median_peaks[condition][block]
            ordered = p[8] < p[11] < p[14]
            gates[f"{condition}_block_{block}_strict_corr_order"] = ordered
            all_pass = all_pass and ordered

    all_cells_near = True
    replicate_support = True
    closer_cells = 0
    cell_diagnostics = {}
    for condition in CONDITIONS:
        cell_diagnostics[condition] = {}
        for block in BLOCKS:
            cell_diagnostics[condition][block] = {}
            for corr in CORRELATION_LENGTHS:
                peak = median_peaks[condition][block][corr]
                error_corr = abs(peak - corr)
                error_block = abs(peak - block)
                near_count = sum(
                    abs(x - corr) <= MAX_CORRELATION_ERROR
                    for x in replicate_peaks[condition][block][corr]
                )
                closer = error_corr + MIN_CLOSER_MARGIN <= error_block
                all_cells_near = all_cells_near and error_corr <= MAX_CORRELATION_ERROR
                replicate_support = replicate_support and near_count >= MIN_REPLICATES_NEAR
                closer_cells += int(closer)
                cell_diagnostics[condition][block][corr] = {
                    "median_peak": peak,
                    "correlation_error": error_corr,
                    "nominal_block_error": error_block,
                    "replicate_near_count": near_count,
                    "closer_to_correlation_by_two": closer,
                }

    gates["all_medians_within_two_of_correlation_length"] = all_cells_near
    gates["all_cells_replicate_support"] = replicate_support
    gates["closer_to_correlation_than_nominal_block"] = closer_cells >= MIN_CLOSER_CELLS
    all_pass = all_pass and all_cells_near and replicate_support and closer_cells >= MIN_CLOSER_CELLS

    block_deltas = {}
    block_invariant = True
    for condition in CONDITIONS:
        block_deltas[condition] = {}
        for corr in CORRELATION_LENGTHS:
            delta = abs(
                median_peaks[condition][3][corr] - median_peaks[condition][6][corr]
            )
            block_deltas[condition][corr] = delta
            block_invariant = block_invariant and delta <= MAX_BLOCK_DELTA_AT_FIXED_L
    gates["nominal_block_invariance"] = block_invariant
    all_pass = all_pass and block_invariant

    boundary_deltas = {}
    robust = 0
    for block in BLOCKS:
        boundary_deltas[block] = {}
        for corr in CORRELATION_LENGTHS:
            delta = abs(
                median_peaks["reflected"][block][corr]
                - median_peaks["self_padded"][block][corr]
            )
            boundary_deltas[block][corr] = delta
            robust += int(delta <= MAX_BOUNDARY_DELTA)
    boundary_robust = robust >= MIN_BOUNDARY_ROBUST_CELLS
    gates["boundary_robustness"] = boundary_robust
    all_pass = all_pass and boundary_robust

    return {
        "status": "NOT_FALSIFIED_BY_DATA" if all_pass else "FALSIFIED_BY_DATA",
        "median_peaks": median_peaks,
        "replicate_peaks": replicate_peaks,
        "cell_diagnostics": cell_diagnostics,
        "nominal_block_peak_deltas": block_deltas,
        "closer_to_correlation_cells": closer_cells,
        "boundary_peak_deltas": boundary_deltas,
        "boundary_robust_cells": robust,
        "gates": gates,
    }
