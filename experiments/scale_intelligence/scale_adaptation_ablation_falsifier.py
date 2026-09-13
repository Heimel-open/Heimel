#!/usr/bin/env python3
"""Evaluate the preregistered SCALE-ADAPTATION-04 factorial ablation."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any, Iterable, Mapping

CONDITIONS = ("baseline", "carryover_only", "delta_only", "joint")
REQUIRED_INVARIANTS = (
    "node_set",
    "topology",
    "initial_state",
    "taskset",
    "compute_budget",
    "update_rule",
)


def _signature(trial: Mapping[str, Any]) -> tuple[str, ...]:
    inv = trial["invariants"]
    return tuple(str(inv[name]) for name in REQUIRED_INVARIANTS)


def evaluate(
    trials: Iterable[Mapping[str, Any]],
    *,
    baseline_ceiling: float = 0.10,
    joint_gain_floor: float = 0.02,
    single_gain_ceiling: float = 0.01,
    joint_excess_floor: float = 0.02,
    min_positive_scales: int = 4,
    min_replicates: int = 3,
) -> dict[str, Any]:
    rows = list(trials)
    if not rows:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no trials"}

    signatures = {_signature(row) for row in rows}
    if len(signatures) != 1:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "non-enabler invariants changed across trials",
        }

    grouped: dict[tuple[float, int], dict[str, float]] = defaultdict(dict)
    scales: set[float] = set()
    reps_by_scale: dict[float, set[int]] = defaultdict(set)

    for row in rows:
        condition = str(row["condition"])
        if condition not in CONDITIONS:
            raise ValueError(f"unknown condition: {condition}")
        score = float(row["counterfactual_adaptation"])
        if not 0.0 <= score <= 1.0:
            raise ValueError("counterfactual_adaptation must be in [0,1]")
        scale = float(row["interaction_scale"])
        replicate = int(row["replicate"])
        key = (scale, replicate)
        if condition in grouped[key]:
            raise ValueError(f"duplicate condition {condition} for {key}")
        grouped[key][condition] = score
        scales.add(scale)
        reps_by_scale[scale].add(replicate)

    if len(scales) != 5:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "exactly five preregistered scales are required",
            "observed_scales": sorted(scales),
        }

    if any(len(reps_by_scale[s]) < min_replicates for s in scales):
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "one or more scales lack paired replicates",
        }

    incomplete = [key for key, values in grouped.items() if set(values) != set(CONDITIONS)]
    if incomplete:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "one or more paired trials lack a factorial condition",
            "incomplete_pairs": [list(key) for key in sorted(incomplete)],
        }

    condition_means = {
        condition: mean(values[condition] for values in grouped.values())
        for condition in CONDITIONS
    }
    baseline = condition_means["baseline"]
    gains = {
        condition: condition_means[condition] - baseline
        for condition in ("carryover_only", "delta_only", "joint")
    }

    scale_means: dict[float, dict[str, float]] = {}
    for scale in sorted(scales):
        keys = [key for key in grouped if key[0] == scale]
        scale_means[scale] = {
            condition: mean(grouped[key][condition] for key in keys)
            for condition in CONDITIONS
        }

    positive_joint_scales = sum(
        scale_means[scale]["joint"] - scale_means[scale]["baseline"] > 0.0
        for scale in scales
    )
    best_single_gain = max(gains["carryover_only"], gains["delta_only"])
    joint_excess = gains["joint"] - best_single_gain
    independent = [
        condition
        for condition in ("carryover_only", "delta_only")
        if gains[condition] > single_gain_ceiling
    ]

    base_result = {
        "condition_means": condition_means,
        "paired_gains_vs_baseline": gains,
        "joint_excess_over_best_single": joint_excess,
        "joint_positive_gain_scales": positive_joint_scales,
        "independently_sufficient_at_effect_floor": independent,
        "scale_means": scale_means,
    }

    if baseline > baseline_ceiling:
        return {
            "status": "FALSIFIED_BY_DATA",
            "reason": "baseline no longer satisfies the frozen low-adaptation control",
            **base_result,
        }
    if gains["joint"] < joint_gain_floor:
        return {
            "status": "FALSIFIED_BY_DATA",
            "reason": "joint carryover+delta effect did not replicate",
            **base_result,
        }
    if independent:
        return {
            "status": "FALSIFIED_BY_DATA",
            "reason": "a single ablated component is independently sufficient at the preregistered effect floor",
            **base_result,
        }
    if joint_excess < joint_excess_floor:
        return {
            "status": "FALSIFIED_BY_DATA",
            "reason": "joint condition does not exceed the best single component by the frozen margin",
            **base_result,
        }
    if positive_joint_scales < min_positive_scales:
        return {
            "status": "FALSIFIED_BY_DATA",
            "reason": "joint gain is not positive across enough scales",
            **base_result,
        }

    return {
        "status": "NOT_FALSIFIED_BY_DATA",
        "reason": "joint carryover+delta effect survives while neither single component reaches the effect floor",
        **base_result,
    }
