#!/usr/bin/env python3
"""Evaluate SCALE-SEPARATION-02: scale-sensitive integration vs scale-insensitive adaptation."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from statistics import mean
from typing import Any, Iterable, Mapping

INTEGRATION_METRICS = (
    "task_success",
    "cross_context_transfer",
    "distributed_integration",
)
ADAPTATION_METRIC = "counterfactual_adaptation"
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
    min_replicates: int = 3,
    min_scales: int = 5,
    integration_spread_min: float = 0.08,
    adaptation_spread_max: float = 0.03,
    adaptation_mean_max: float = 0.10,
    common_peak_min_metrics: int = 2,
) -> dict[str, Any]:
    grouped: dict[float, list[Mapping[str, Any]]] = defaultdict(list)
    signatures: set[tuple[str, ...]] = set()

    for trial in trials:
        scale = float(trial["interaction_scale"])
        if scale <= 0:
            raise ValueError("interaction_scale must be > 0")
        phenotype = trial["phenotype"]
        for metric in (*INTEGRATION_METRICS, ADAPTATION_METRIC):
            value = float(phenotype[metric])
            if value < 0.0 or value > 1.0:
                raise ValueError("phenotype metrics must be in [0,1]")
        signatures.add(_signature(trial))
        grouped[scale].append(trial)

    if len(signatures) != 1:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "non-scale invariants changed across trials",
        }

    scales = sorted(scale for scale, rows in grouped.items() if len(rows) >= min_replicates)
    if len(scales) < min_scales:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "too few scales have enough replicates",
            "eligible_scales": scales,
        }

    metric_means: dict[str, dict[float, float]] = {}
    for metric in (*INTEGRATION_METRICS, ADAPTATION_METRIC):
        metric_means[metric] = {
            scale: mean(float(row["phenotype"][metric]) for row in grouped[scale])
            for scale in scales
        }

    integration_spreads = {
        metric: max(metric_means[metric].values()) - min(metric_means[metric].values())
        for metric in INTEGRATION_METRICS
    }
    scale_sensitive = {
        metric: spread >= integration_spread_min
        for metric, spread in integration_spreads.items()
    }

    peaks = {
        metric: max(scales, key=lambda scale: metric_means[metric][scale])
        for metric in INTEGRATION_METRICS
    }
    peak_counts = {scale: list(peaks.values()).count(scale) for scale in scales}
    common_peak_scale = max(peak_counts, key=peak_counts.get)
    common_peak_count = peak_counts[common_peak_scale]

    adaptation_values = metric_means[ADAPTATION_METRIC]
    adaptation_spread = max(adaptation_values.values()) - min(adaptation_values.values())
    adaptation_mean = mean(adaptation_values.values())

    integration_pass = all(scale_sensitive.values()) and common_peak_count >= common_peak_min_metrics
    adaptation_pass = (
        adaptation_spread <= adaptation_spread_max
        and adaptation_mean <= adaptation_mean_max
    )

    if integration_pass and adaptation_pass:
        status = "NOT_FALSIFIED_BY_DATA"
        reason = "integration/transfer are materially scale-sensitive while adaptation remains flat and low"
    elif not integration_pass:
        status = "FALSIFIED_BY_DATA"
        reason = "integration/transfer do not meet the preregistered scale-sensitivity pattern"
    else:
        status = "FALSIFIED_BY_DATA"
        reason = "counterfactual adaptation is not flat-low under scale intervention"

    return {
        "status": status,
        "reason": reason,
        "metric_means": metric_means,
        "integration_spreads": integration_spreads,
        "scale_sensitive": scale_sensitive,
        "peak_scales": peaks,
        "common_peak_scale": common_peak_scale,
        "common_peak_count": common_peak_count,
        "adaptation_spread": adaptation_spread,
        "adaptation_mean": adaptation_mean,
        "thresholds": {
            "integration_spread_min": integration_spread_min,
            "adaptation_spread_max": adaptation_spread_max,
            "adaptation_mean_max": adaptation_mean_max,
            "common_peak_min_metrics": common_peak_min_metrics,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input")
    args = parser.parse_args()
    with open(args.input, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    trials = payload["trials"] if isinstance(payload, dict) else payload
    print(json.dumps(evaluate(trials), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
