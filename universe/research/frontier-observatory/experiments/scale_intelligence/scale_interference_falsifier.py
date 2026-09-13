#!/usr/bin/env python3
"""Frozen evaluator for SCALE-INTERFERENCE-19."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean

SCALES = tuple(range(4, 16))
CONDITIONS = ("reflected", "self_padded")
TASKS = (
    "seg_b7", "seg_b10", "seg_b13",
    "markov_b3_l8", "markov_b3_l11", "markov_b3_l14",
    "markov_b6_l8", "markov_b6_l11", "markov_b6_l14",
)
REPLICATES = 5
MAX_NUMERICAL_ERROR = 1e-12

PRIMARY_CONDITION = "self_padded"
PRIMARY_TASK = "seg_b13"
LOW_SCALE = 7
HIGH_SCALE = 13

MIN_NATIVE_ADV = 0.020
MIN_NATIVE_POSITIVE_REPLICATES = 4
MAX_SCRAMBLED_ADV_ABS = 0.010
MIN_COLLAPSE = 0.015
MIN_REPLICATE_COLLAPSE = 0.010
MIN_COLLAPSE_REPLICATES = 4
MIN_SPECIFICITY_GAP = 0.008


def _peak(scale_scores):
    m = max(scale_scores.values())
    tied = [s for s in SCALES if scale_scores[s] == m]
    return mean(tied)


def evaluate(trials):
    if not trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no_trials"}

    by_cell = defaultdict(list)
    invariant_sets = defaultdict(set)
    seed_map = defaultdict(set)
    max_numerical_error = 0.0
    max_energy_error = 0.0

    for t in trials:
        try:
            condition = str(t["boundary_condition"])
            task = str(t["task_id"])
            scale = int(t["interaction_scale"])
            replicate = int(t["replicate"])
            seed = int(t["seed"])
            native = float(t["native_capability"])
            scrambled = float(t["scrambled_capability"])
            err = max(
                float(t["svd_reconstruction_max_error"]),
                float(t["modal_output_reconstruction_max_error"]),
                float(t["state_decomposition_max_error"]),
            )
            energy_err = float(t["scramble_energy_max_error"])
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
        if not all(math.isfinite(v) and 0.0 <= v <= 1.0 for v in (native, scrambled)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invalid_score"}
        if not math.isfinite(err) or not math.isfinite(energy_err) or err < 0 or energy_err < 0:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invalid_numerical_error"}

        max_numerical_error = max(max_numerical_error, err)
        max_energy_error = max(max_energy_error, energy_err)
        by_cell[(condition, task, scale)].append(t)
        invariant_sets[condition].add(invariants)
        seed_map[(condition, replicate)].add(seed)

    if max_numerical_error > MAX_NUMERICAL_ERROR:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "numerical_reconstruction_failed",
            "max_numerical_error": max_numerical_error,
        }
    if max_energy_error > MAX_NUMERICAL_ERROR:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "scramble_energy_not_preserved",
            "max_scramble_energy_error": max_energy_error,
        }
    if any(len(invariant_sets[c]) != 1 for c in CONDITIONS):
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "invariant_drift"}

    for replicate in range(REPLICATES):
        ss = [seed_map[(c, replicate)] for c in CONDITIONS]
        if any(len(x) != 1 for x in ss):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "seed_pairing"}
        if len({next(iter(x)) for x in ss}) != 1:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "cross_condition_seed_mismatch"}

    expected = {(c, t, s) for c in CONDITIONS for t in TASKS for s in SCALES}
    if set(by_cell) != expected:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "condition_coverage"}

    for cell in expected:
        rows = by_cell[cell]
        if len(rows) != REPLICATES:
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_coverage"}
        if sorted(int(x["replicate"]) for x in rows) != list(range(REPLICATES)):
            return {"status": "INSUFFICIENT_EVIDENCE", "reason": "replicate_pairing"}

    def row_for(condition, task, scale, replicate):
        return next(
            x for x in by_cell[(condition, task, scale)]
            if int(x["replicate"]) == replicate
        )

    native_adv = []
    scrambled_adv = []
    collapse = []
    for r in range(REPLICATES):
        lo = row_for(PRIMARY_CONDITION, PRIMARY_TASK, LOW_SCALE, r)
        hi = row_for(PRIMARY_CONDITION, PRIMARY_TASK, HIGH_SCALE, r)
        na = float(hi["native_capability"]) - float(lo["native_capability"])
        sa = float(hi["scrambled_capability"]) - float(lo["scrambled_capability"])
        native_adv.append(na)
        scrambled_adv.append(sa)
        collapse.append(na - sa)

    native_adv_agg = mean(native_adv)
    scrambled_adv_agg = mean(scrambled_adv)
    collapse_agg = mean(collapse)
    native_positive = sum(x > 0 for x in native_adv)
    collapse_support = sum(x >= MIN_REPLICATE_COLLAPSE for x in collapse)

    def aggregate_effect(task, scale):
        rows = by_cell[(PRIMARY_CONDITION, task, scale)]
        return mean(float(x["native_capability"]) - float(x["scrambled_capability"]) for x in rows)

    key_drop = aggregate_effect("seg_b13", 13)
    control_abs = mean((
        abs(aggregate_effect("seg_b7", 7)),
        abs(aggregate_effect("seg_b10", 9)),
    ))
    specificity_gap = key_drop - control_abs

    fresh_native_reproduced = (
        native_adv_agg >= MIN_NATIVE_ADV
        and native_positive >= MIN_NATIVE_POSITIVE_REPLICATES
    )

    # Diagnostics: native/scrambled aggregate curves and peaks.
    aggregate_curves = {c: {t: {} for t in TASKS} for c in CONDITIONS}
    median_replicate_peaks = {
        metric: {c: {} for c in CONDITIONS}
        for metric in ("native_capability", "scrambled_capability")
    }
    for c in CONDITIONS:
        for task in TASKS:
            for s in SCALES:
                rows = by_cell[(c, task, s)]
                aggregate_curves[c][task][s] = {
                    "native_capability": mean(float(x["native_capability"]) for x in rows),
                    "scrambled_capability": mean(float(x["scrambled_capability"]) for x in rows),
                    "absolute_scramble_effect": mean(
                        abs(float(x["native_capability"]) - float(x["scrambled_capability"]))
                        for x in rows
                    ),
                }
            for metric in ("native_capability", "scrambled_capability"):
                peaks = []
                for r in range(REPLICATES):
                    scores = {
                        s: float(row_for(c, task, s, r)[metric])
                        for s in SCALES
                    }
                    peaks.append(_peak(scores))
                peaks_sorted = sorted(peaks)
                median_replicate_peaks[metric][c][task] = {
                    "replicate_peaks": peaks,
                    "median_peak": peaks_sorted[len(peaks_sorted)//2],
                }

    gates = {
        "numerical_reconstruction": max_numerical_error <= MAX_NUMERICAL_ERROR,
        "scramble_energy_preserved": max_energy_error <= MAX_NUMERICAL_ERROR,
        "native_advantage_ge_0_020": native_adv_agg >= MIN_NATIVE_ADV,
        "native_positive_4_of_5": native_positive >= MIN_NATIVE_POSITIVE_REPLICATES,
        "scrambled_advantage_abs_le_0_010": abs(scrambled_adv_agg) <= MAX_SCRAMBLED_ADV_ABS,
        "aggregate_collapse_ge_0_015": collapse_agg >= MIN_COLLAPSE,
        "replicate_collapse_4_of_5": collapse_support >= MIN_COLLAPSE_REPLICATES,
        "specificity_gap_ge_0_008": specificity_gap >= MIN_SPECIFICITY_GAP,
    }

    if not fresh_native_reproduced:
        status = "INSUFFICIENT_EVIDENCE"
        reason = "fixed_native_advantage_not_reproduced"
    else:
        causal_gates = [
            gates["scrambled_advantage_abs_le_0_010"],
            gates["aggregate_collapse_ge_0_015"],
            gates["replicate_collapse_4_of_5"],
            gates["specificity_gap_ge_0_008"],
        ]
        status = "NOT_FALSIFIED_BY_DATA" if all(causal_gates) else "FALSIFIED_BY_DATA"
        reason = "causal_interference_survived" if status == "NOT_FALSIFIED_BY_DATA" else "causal_interference_gates_failed"

    return {
        "status": status,
        "reason": reason,
        "max_numerical_error": max_numerical_error,
        "max_scramble_energy_error": max_energy_error,
        "primary": {
            "native_advantages": native_adv,
            "scrambled_advantages": scrambled_adv,
            "collapse_by_replicate": collapse,
            "native_advantage_mean": native_adv_agg,
            "scrambled_advantage_mean": scrambled_adv_agg,
            "collapse_mean": collapse_agg,
            "native_positive_replicates": native_positive,
            "collapse_support_replicates": collapse_support,
            "key_scale13_scrambling_drop": key_drop,
            "control_mean_absolute_scrambling_effect": control_abs,
            "specificity_gap": specificity_gap,
        },
        "aggregate_curves": aggregate_curves,
        "peak_diagnostics": median_replicate_peaks,
        "gates": gates,
    }
