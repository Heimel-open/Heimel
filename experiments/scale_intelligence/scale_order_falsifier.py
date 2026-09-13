#!/usr/bin/env python3
"""Evaluate SCALE-ORDER-05 without retuning after observation."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean

REQUIRED_INVARIANTS = (
    "node_set",
    "topology",
    "initial_state",
    "taskset",
    "compute_budget",
    "update_rule",
)


def _signature(trial: dict) -> tuple:
    invariants = trial.get("invariants", {})
    return tuple((key, invariants.get(key)) for key in REQUIRED_INVARIANTS)


def evaluate(
    trials: list[dict],
    *,
    min_replicates: int = 5,
    extreme_capability_margin: float = 0.05,
    integration_margin: float = 0.05,
    differentiation_margin: float = 0.05,
    balance_tolerance: float = 0.02,
    min_replicate_support: int = 4,
) -> dict:
    if not trials:
        return {"status": "INSUFFICIENT_EVIDENCE", "reason": "no trials"}

    signatures = {_signature(trial) for trial in trials}
    if len(signatures) != 1:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "non-scale invariants changed across trials",
        }

    grouped: dict[int, list[dict]] = defaultdict(list)
    for trial in trials:
        scale = int(trial["interaction_scale"])
        for metric in ("integration", "differentiation", "capability", "balance"):
            value = float(trial[metric])
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{metric} must be in [0,1]")
        grouped[scale].append(trial)

    eligible = {
        scale: rows for scale, rows in grouped.items() if len(rows) >= min_replicates
    }
    if len(eligible) < 5:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "fewer than five scales have the preregistered replicate count",
        }

    scales = sorted(eligible)
    low_scale, high_scale = scales[0], scales[-1]
    interior = scales[1:-1]

    by_scale = {
        scale: {
            metric: mean(float(row[metric]) for row in eligible[scale])
            for metric in ("integration", "differentiation", "capability", "balance")
        }
        for scale in scales
    }

    peak_scale = max(interior, key=lambda scale: by_scale[scale]["capability"])
    peak_capability = by_scale[peak_scale]["capability"]
    max_balance = max(values["balance"] for values in by_scale.values())

    low_capability_gap = peak_capability - by_scale[low_scale]["capability"]
    high_capability_gap = peak_capability - by_scale[high_scale]["capability"]
    low_integration_gap = (
        by_scale[peak_scale]["integration"] - by_scale[low_scale]["integration"]
    )
    high_differentiation_gap = (
        by_scale[peak_scale]["differentiation"]
        - by_scale[high_scale]["differentiation"]
    )
    balance_gap = max_balance - by_scale[peak_scale]["balance"]

    support = 0
    for replicate in range(min_replicates):
        try:
            peak_row = eligible[peak_scale][replicate]
            low_row = eligible[low_scale][replicate]
            high_row = eligible[high_scale][replicate]
        except IndexError:
            continue
        if (
            float(peak_row["capability"]) > float(low_row["capability"])
            and float(peak_row["capability"]) > float(high_row["capability"])
        ):
            support += 1

    gates = {
        "interior_peak_beats_low_extreme": low_capability_gap >= extreme_capability_margin,
        "interior_peak_beats_high_extreme": high_capability_gap >= extreme_capability_margin,
        "integration_above_low_extreme": low_integration_gap >= integration_margin,
        "differentiation_above_high_extreme": high_differentiation_gap
        >= differentiation_margin,
        "peak_lies_in_balance_zone": balance_gap <= balance_tolerance,
        "replicate_support": support >= min_replicate_support,
    }

    status = "NOT_FALSIFIED_BY_DATA" if all(gates.values()) else "FALSIFIED_BY_DATA"
    reason = (
        "capability peak lies in a preregistered integration-differentiation transition zone"
        if status == "NOT_FALSIFIED_BY_DATA"
        else "one or more preregistered transition-zone gates failed"
    )

    return {
        "status": status,
        "reason": reason,
        "peak_scale": peak_scale,
        "by_scale": by_scale,
        "low_capability_gap": low_capability_gap,
        "high_capability_gap": high_capability_gap,
        "low_integration_gap": low_integration_gap,
        "high_differentiation_gap": high_differentiation_gap,
        "balance_gap": balance_gap,
        "replicate_support": support,
        "gates": gates,
        "thresholds": {
            "min_replicates": min_replicates,
            "extreme_capability_margin": extreme_capability_margin,
            "integration_margin": integration_margin,
            "differentiation_margin": differentiation_margin,
            "balance_tolerance": balance_tolerance,
            "min_replicate_support": min_replicate_support,
        },
    }
