#!/usr/bin/env python3
"""Falsify a scale-dependent intelligence hypothesis under fixed invariants."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from statistics import mean
from typing import Any, Iterable, Mapping

METRICS = (
    "task_success",
    "cross_context_transfer",
    "distributed_integration",
    "counterfactual_adaptation",
)

REQUIRED_INVARIANTS = (
    "node_set",
    "topology",
    "initial_state",
    "taskset",
    "compute_budget",
    "update_rule",
)


def phenotype_score(trial: Mapping[str, Any]) -> float:
    phenotype = trial["phenotype"]
    values = [float(phenotype[name]) for name in METRICS]
    if any(value < 0.0 or value > 1.0 for value in values):
        raise ValueError("phenotype metrics must be in [0,1]")
    return mean(values)


def _invariant_signature(trial: Mapping[str, Any]) -> tuple[str, ...]:
    invariants = trial["invariants"]
    return tuple(str(invariants[name]) for name in REQUIRED_INVARIANTS)


def evaluate(
    trials: Iterable[Mapping[str, Any]],
    *,
    phenotype_threshold: float = 0.70,
    recovery_threshold: float = 0.80,
    scale_margin: float = 0.15,
    min_replicates: int = 3,
    min_scales: int = 3,
) -> dict[str, Any]:
    grouped: dict[float, list[float]] = defaultdict(list)
    signatures: set[tuple[str, ...]] = set()

    for trial in trials:
        scale = float(trial["interaction_scale"])
        if scale <= 0:
            raise ValueError("interaction_scale must be > 0")
        signatures.add(_invariant_signature(trial))
        grouped[scale].append(phenotype_score(trial))

    if len(signatures) != 1:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "non-scale invariants changed across trials",
            "invariant_signatures": len(signatures),
        }

    eligible = sorted(
        scale for scale, scores in grouped.items() if len(scores) >= min_replicates
    )
    if len(eligible) < min_scales:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "too few interaction scales have enough replicates",
            "eligible_scales": eligible,
        }

    means = {scale: mean(grouped[scale]) for scale in eligible}
    recovery = {
        scale: sum(score >= phenotype_threshold for score in grouped[scale])
        / len(grouped[scale])
        for scale in eligible
    }

    qualifying = [
        scale for scale in eligible if recovery[scale] >= recovery_threshold
    ]
    nonqualifying = [
        scale for scale in eligible if recovery[scale] < recovery_threshold
    ]

    if not qualifying:
        return {
            "status": "FALSIFIED_BY_DATA",
            "reason": "no tested scale reaches the preregistered phenotype regime",
            "scale_means": means,
            "scale_recovery": recovery,
        }

    if not nonqualifying:
        return {
            "status": "FALSIFIED_BY_DATA",
            "reason": "phenotype is present across all tested scales; no scale transition observed",
            "scale_means": means,
            "scale_recovery": recovery,
        }

    pairs = [
        (abs(means[q] - means[n]), q, n)
        for q in qualifying
        for n in nonqualifying
    ]
    observed_margin, qualifying_scale, nonqualifying_scale = max(pairs)

    if observed_margin < scale_margin:
        return {
            "status": "FALSIFIED_BY_DATA",
            "reason": "threshold crossing is too small to meet the preregistered scale margin",
            "scale_means": means,
            "scale_recovery": recovery,
            "scale_margin_observed": observed_margin,
        }

    direction = (
        "emerges_with_scale"
        if qualifying_scale > nonqualifying_scale
        else "disappears_with_scale"
    )

    return {
        "status": "NOT_FALSIFIED_BY_DATA",
        "reason": "fixed-invariant trials show a reproducible scale-dependent phenotype regime",
        "scale_means": means,
        "scale_recovery": recovery,
        "qualifying_scale": qualifying_scale,
        "nonqualifying_scale": nonqualifying_scale,
        "scale_margin_observed": observed_margin,
        "direction": direction,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="JSON file containing a list of trials")
    parser.add_argument("--phenotype-threshold", type=float, default=0.70)
    parser.add_argument("--recovery-threshold", type=float, default=0.80)
    parser.add_argument("--scale-margin", type=float, default=0.15)
    parser.add_argument("--min-replicates", type=int, default=3)
    parser.add_argument("--min-scales", type=int, default=3)
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as handle:
        trials = json.load(handle)

    result = evaluate(
        trials,
        phenotype_threshold=args.phenotype_threshold,
        recovery_threshold=args.recovery_threshold,
        scale_margin=args.scale_margin,
        min_replicates=args.min_replicates,
        min_scales=args.min_scales,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
