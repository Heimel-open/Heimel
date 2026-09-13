#!/usr/bin/env python3
"""Evaluate SCALE-ADAPTATION-03 paired adaptation-enabler trials."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any, Iterable, Mapping

CONDITIONS = ("baseline", "temporal_carryover")
REQUIRED_INVARIANTS = (
    "node_set",
    "topology",
    "initial_state",
    "taskset",
    "compute_budget",
    "update_rule",
)


def _signature(trial: Mapping[str, Any]) -> tuple[str, ...]:
    invariants = trial["invariants"]
    return tuple(str(invariants[name]) for name in REQUIRED_INVARIANTS)


def evaluate(
    trials: Iterable[Mapping[str, Any]],
    *,
    scales: tuple[int, ...] = (1, 2, 4, 8, 16),
    min_replicates: int = 3,
    baseline_ceiling: float = 0.10,
    min_mean_gain: float = 0.02,
    min_positive_scales: int = 4,
) -> dict[str, Any]:
    grouped: dict[tuple[str, int], dict[int, float]] = defaultdict(dict)
    signatures: set[tuple[str, ...]] = set()

    for trial in trials:
        condition = str(trial["condition"])
        if condition not in CONDITIONS:
            raise ValueError(f"unknown condition: {condition}")
        scale = int(trial["interaction_scale"])
        replicate = int(trial["replicate"])
        score = float(trial["counterfactual_adaptation"])
        if score < 0.0 or score > 1.0:
            raise ValueError("counterfactual_adaptation must be in [0,1]")
        signatures.add(_signature(trial))
        if replicate in grouped[(condition, scale)]:
            raise ValueError("duplicate condition/scale/replicate")
        grouped[(condition, scale)][replicate] = score

    if len(signatures) != 1:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "non-enabler invariants changed across trials",
            "invariant_signatures": len(signatures),
        }

    expected_scales = tuple(int(scale) for scale in scales)
    for scale in expected_scales:
        baseline = grouped.get(("baseline", scale), {})
        enabled = grouped.get(("temporal_carryover", scale), {})
        if len(baseline) < min_replicates or len(enabled) < min_replicates:
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "reason": "missing required replicates at one or more scales",
                "scale": scale,
            }
        if set(baseline) != set(enabled):
            return {
                "status": "INSUFFICIENT_EVIDENCE",
                "reason": "baseline and enabler replicates are not paired",
                "scale": scale,
            }

    baseline_means: dict[int, float] = {}
    enabled_means: dict[int, float] = {}
    gains: dict[int, float] = {}
    paired_gains: list[float] = []

    for scale in expected_scales:
        baseline = grouped[("baseline", scale)]
        enabled = grouped[("temporal_carryover", scale)]
        baseline_means[scale] = mean(baseline.values())
        enabled_means[scale] = mean(enabled.values())
        gains[scale] = enabled_means[scale] - baseline_means[scale]
        paired_gains.extend(enabled[r] - baseline[r] for r in sorted(baseline))

    baseline_mean = mean(baseline_means.values())
    enabled_mean = mean(enabled_means.values())
    mean_gain = mean(paired_gains)
    positive_scales = sum(gains[scale] > 0.0 for scale in expected_scales)
    gain_spread = max(gains.values()) - min(gains.values())
    enabled_scale_spread = max(enabled_means.values()) - min(enabled_means.values())

    failures = []
    if baseline_mean > baseline_ceiling:
        failures.append("baseline adaptation is above frozen low-adaptation ceiling")
    if mean_gain < min_mean_gain:
        failures.append("temporal carryover gain is below frozen material-gain threshold")
    if positive_scales < min_positive_scales:
        failures.append("temporal carryover does not improve enough tested scales")

    status = "FALSIFIED_BY_DATA" if failures else "NOT_FALSIFIED_BY_DATA"
    reason = "; ".join(failures) if failures else (
        "temporal carryover materially improves paired counterfactual adaptation "
        "while non-enabler invariants remain fixed"
    )

    return {
        "status": status,
        "reason": reason,
        "baseline_mean": baseline_mean,
        "enabled_mean": enabled_mean,
        "mean_gain": mean_gain,
        "positive_scales": positive_scales,
        "baseline_by_scale": baseline_means,
        "enabled_by_scale": enabled_means,
        "gain_by_scale": gains,
        "gain_spread": gain_spread,
        "enabled_scale_spread": enabled_scale_spread,
        "gates": {
            "baseline_ceiling": baseline_ceiling,
            "min_mean_gain": min_mean_gain,
            "min_positive_scales": min_positive_scales,
            "min_replicates": min_replicates,
        },
    }
