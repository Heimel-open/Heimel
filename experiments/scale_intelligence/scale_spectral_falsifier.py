#!/usr/bin/env python3
"""Frozen evaluator for SCALE-SPECTRAL-17."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean, median

SCALES = tuple(range(4, 16))
CONDITIONS = ("reflected", "self_padded")
TASKS = (
    "seg_b7", "seg_b10", "seg_b13",
    "markov_b3_l8", "markov_b3_l11", "markov_b3_l14",
    "markov_b6_l8", "markov_b6_l11", "markov_b6_l14",
)
REPLICATES = 5
MAX_DECOMPOSITION_ERROR = 1e-12
MIN_MEDIAN_WITHIN_ONE = 15
MAX_ALL_MEDIAN_ERROR = 2.0
MIN_REPLICATE_WITHIN_TWO = 75
MIN_MEDIAN_SPEARMAN = 0.80
MIN_CURVE_SPEARMAN = 0.80
MIN_CURVE_CELLS = 15
MAX_BOUNDARY_DELTA_ERROR = 1.0
MIN_BOUNDARY_DELTA_TASKS = 7


def _peak(scores: dict[int, float]) -> float:
    maximum = max(scores.values())
    tied = [s for s in SCALES if scores[s] == maximum]
    return mean(tied)


def _ranks(values: list[float]) -> list[float]:
    indexed = sorted(enumerate(values), key=lambda x: x[1])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(indexed):
        j = i + 1
        while j < len(indexed) and indexed[j][1] == indexed[i][1]:
            j += 1
        rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[indexed[k][0]] = rank
        i = j
    return ranks


def _spearman(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or len(a) < 2:
        return float("nan")
    ra = _ranks(a)
    rb = _ranks(b)
    ma = mean(ra)
    mb = mean(rb)
    da = sum((x - ma) ** 2 for x in ra)
    db = sum((x - mb) ** 2 for x in rb)
    if da == 0.0 or db == 0.0:
        return 1.0 if ra == rb else 0.0
    return sum((x - ma) * (y - mb) for x, y in zip(ra, rb)) / math.sqrt(da * db)


def evaluate(trials: list[dict[str, object]]) -> dict[str, object]:
    if not trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no_trials"}

    by_cell = defaultdict(list)
    invariant_sets = defaultdict(set)
    seed_map = defaultdict(set)
    max_decomposition_error = 0.0

    for t in trials:
        try:
            condition = str(t["boundary_condition"])
            task = str(t["task_id"])
            scale = int(t["interaction_scale"])
            replicate = int(t["replicate"])
            seed = int(t["seed"])
            spectral = float(t["spectral_target_fraction"])
            capability = float(t["capability"])
            decomposition_error = float(t["decomposition_max_error"])
            invariants = tuple(sorted(dict(t["condition_invariants"]).items()))
        except (KeyError, TypeError, ValueError):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "malformed_trial"}

        if (
            condition not in CONDITIONS
            or task not in TASKS
            or scale not in SCALES
            or not 0 <= replicate < REPLICATES
        ):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "unexpected_condition"}
        if not all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in (spectral, capability)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invalid_score"}
        if not math.isfinite(decomposition_error) or decomposition_error < 0:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invalid_decomposition_error"}

        max_decomposition_error = max(max_decomposition_error, decomposition_error)
        by_cell[(condition, task, scale)].append(t)
        invariant_sets[condition].add(invariants)
        seed_map[(condition, replicate)].add(seed)

    if max_decomposition_error > MAX_DECOMPOSITION_ERROR:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "operator_decomposition_failed",
            "max_decomposition_error": max_decomposition_error,
        }

    if any(len(invariant_sets[c]) != 1 for c in CONDITIONS):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invariant_drift"}

    for replicate in range(REPLICATES):
        seeds = [seed_map[(c, replicate)] for c in CONDITIONS]
        if any(len(s) != 1 for s in seeds):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "seed_pairing"}
        if len({next(iter(s)) for s in seeds}) != 1:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "cross_condition_seed_mismatch"}

    expected = {(c, t, s) for c in CONDITIONS for t in TASKS for s in SCALES}
    if set(by_cell) != expected:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "condition_coverage"}
    for cell in expected:
        rows = by_cell[cell]
        if len(rows) != REPLICATES:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_coverage"}
        if sorted(int(r["replicate"]) for r in rows) != list(range(REPLICATES)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_pairing"}

    replicate_peaks = {
        metric: {c: {t: [] for t in TASKS} for c in CONDITIONS}
        for metric in ("spectral_target_fraction", "capability")
    }
    median_peaks = {
        metric: {c: {} for c in CONDITIONS}
        for metric in ("spectral_target_fraction", "capability")
    }
    aggregate_curves = {
        c: {t: {} for t in TASKS}
        for c in CONDITIONS
    }

    for condition in CONDITIONS:
        for task in TASKS:
            for scale in SCALES:
                rows = by_cell[(condition, task, scale)]
                aggregate_curves[condition][task][scale] = {
                    "spectral_target_fraction": mean(float(r["spectral_target_fraction"]) for r in rows),
                    "capability": mean(float(r["capability"]) for r in rows),
                    "residual_power": mean(float(r["residual_power"]) for r in rows),
                }

            for metric in ("spectral_target_fraction", "capability"):
                peaks = []
                for replicate in range(REPLICATES):
                    scores = {
                        scale: float(next(
                            r for r in by_cell[(condition, task, scale)]
                            if int(r["replicate"]) == replicate
                        )[metric])
                        for scale in SCALES
                    }
                    peaks.append(_peak(scores))
                replicate_peaks[metric][condition][task] = peaks
                median_peaks[metric][condition][task] = median(peaks)

    median_errors = {}
    within_one = 0
    all_within_two = True
    replicate_within_two = 0
    median_spectral = []
    median_capability = []
    curve_spearman = {}
    curve_pass_cells = 0

    for condition in CONDITIONS:
        median_errors[condition] = {}
        curve_spearman[condition] = {}
        for task in TASKS:
            sp = median_peaks["spectral_target_fraction"][condition][task]
            cp = median_peaks["capability"][condition][task]
            err = abs(sp - cp)
            median_errors[condition][task] = err
            within_one += int(err <= 1.0)
            all_within_two = all_within_two and err <= MAX_ALL_MEDIAN_ERROR
            median_spectral.append(sp)
            median_capability.append(cp)

            sr = replicate_peaks["spectral_target_fraction"][condition][task]
            cr = replicate_peaks["capability"][condition][task]
            replicate_within_two += sum(abs(a - b) <= 2.0 for a, b in zip(sr, cr))

            xs = [aggregate_curves[condition][task][s]["spectral_target_fraction"] for s in SCALES]
            ys = [aggregate_curves[condition][task][s]["capability"] for s in SCALES]
            rho = _spearman(xs, ys)
            curve_spearman[condition][task] = rho
            curve_pass_cells += int(rho >= MIN_CURVE_SPEARMAN)

    median_rho = _spearman(median_spectral, median_capability)

    boundary_delta_errors = {}
    boundary_delta_pass = 0
    for task in TASKS:
        spectral_delta = (
            median_peaks["spectral_target_fraction"]["self_padded"][task]
            - median_peaks["spectral_target_fraction"]["reflected"][task]
        )
        capability_delta = (
            median_peaks["capability"]["self_padded"][task]
            - median_peaks["capability"]["reflected"][task]
        )
        err = abs(spectral_delta - capability_delta)
        boundary_delta_errors[task] = {
            "spectral_delta": spectral_delta,
            "capability_delta": capability_delta,
            "absolute_error": err,
        }
        boundary_delta_pass += int(err <= MAX_BOUNDARY_DELTA_ERROR)

    gates = {
        "decomposition": max_decomposition_error <= MAX_DECOMPOSITION_ERROR,
        "median_within_one_15_of_18": within_one >= MIN_MEDIAN_WITHIN_ONE,
        "all_medians_within_two": all_within_two,
        "replicate_within_two_75_of_90": replicate_within_two >= MIN_REPLICATE_WITHIN_TWO,
        "median_peak_spearman_ge_0_80": median_rho >= MIN_MEDIAN_SPEARMAN,
        "curve_spearman_15_of_18": curve_pass_cells >= MIN_CURVE_CELLS,
        "boundary_delta_prediction_7_of_9": boundary_delta_pass >= MIN_BOUNDARY_DELTA_TASKS,
    }

    return {
        "status": "NOT_FALSIFIED_BY_DATA" if all(gates.values()) else "FALSIFIED_BY_DATA",
        "max_decomposition_error": max_decomposition_error,
        "median_peaks": median_peaks,
        "replicate_peaks": replicate_peaks,
        "median_peak_errors": median_errors,
        "median_within_one_cells": within_one,
        "replicate_within_two_pairs": replicate_within_two,
        "median_peak_spearman": median_rho,
        "curve_spearman": curve_spearman,
        "curve_spearman_pass_cells": curve_pass_cells,
        "boundary_delta_errors": boundary_delta_errors,
        "boundary_delta_pass_tasks": boundary_delta_pass,
        "aggregate_curves": aggregate_curves,
        "gates": gates,
    }
