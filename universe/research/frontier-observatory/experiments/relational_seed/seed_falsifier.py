#!/usr/bin/env python3
"""Evaluate minimum relational-seed recovery with matched shuffle controls.

This harness does not measure consciousness. It evaluates a preregistered
consciousness-like integrated-availability phenotype over supplied trials.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from statistics import mean
from typing import Any, Iterable, Mapping

METRICS = (
    "cross_access",
    "workspace_integration",
    "temporal_continuity",
    "history_dependence",
    "counterfactual_reorganization",
    "self_effect_on_next_selection",
)


def phenotype_score(trial: Mapping[str, Any]) -> float:
    phenotype = trial["phenotype"]
    values = [float(phenotype[name]) for name in METRICS]
    if any(value < 0.0 or value > 1.0 for value in values):
        raise ValueError("phenotype metrics must be in [0,1]")
    return mean(values)


def evaluate(
    trials: Iterable[Mapping[str, Any]],
    *,
    phenotype_threshold: float = 0.70,
    recovery_threshold: float = 0.80,
    relation_margin: float = 0.15,
    min_replicates: int = 3,
) -> dict[str, Any]:
    grouped: dict[tuple[str, int], list[float]] = defaultdict(list)

    for trial in trials:
        seed_size = int(trial["seed_size"])
        if seed_size < 0:
            raise ValueError("seed_size must be >= 0")
        condition = str(trial["condition"])
        grouped[(condition, seed_size)].append(phenotype_score(trial))

    intact_sizes = sorted(
        seed_size
        for (condition, seed_size), scores in grouped.items()
        if condition == "intact" and len(scores) >= min_replicates
    )

    if not intact_sizes:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "no intact seed size has enough replicates",
        }

    recovery: dict[int, float] = {}
    for seed_size in intact_sizes:
        scores = grouped[("intact", seed_size)]
        recovery[seed_size] = sum(
            score >= phenotype_threshold for score in scores
        ) / len(scores)

    qualifying = [
        seed_size
        for seed_size, rate in recovery.items()
        if rate >= recovery_threshold
    ]

    if not qualifying:
        return {
            "status": "FALSIFIED_BY_DATA",
            "reason": "no tested intact seed size reaches recovery threshold",
            "recovery": recovery,
        }

    s_star = min(qualifying)
    shuffled = grouped.get(("shuffled", s_star), [])

    if len(shuffled) < min_replicates:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "reason": "missing shuffled control at candidate s*",
            "s_star": s_star,
            "recovery": recovery,
        }

    intact_mean = mean(grouped[("intact", s_star)])
    shuffled_mean = mean(shuffled)
    observed_margin = intact_mean - shuffled_mean

    if observed_margin < relation_margin:
        status = "FALSIFIED_BY_DATA"
        reason = "relation shuffle preserves too much phenotype"
    else:
        status = "NOT_FALSIFIED_BY_DATA"
        reason = "candidate minimum seed and relation-specific margin observed"

    return {
        "status": status,
        "reason": reason,
        "s_star": s_star,
        "recovery": recovery,
        "intact_mean": intact_mean,
        "shuffled_mean": shuffled_mean,
        "relation_margin_observed": observed_margin,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="JSON file containing a list of trials")
    parser.add_argument("--phenotype-threshold", type=float, default=0.70)
    parser.add_argument("--recovery-threshold", type=float, default=0.80)
    parser.add_argument("--relation-margin", type=float, default=0.15)
    parser.add_argument("--min-replicates", type=int, default=3)
    args = parser.parse_args()

    with open(args.input, "r", encoding="utf-8") as handle:
        trials = json.load(handle)

    result = evaluate(
        trials,
        phenotype_threshold=args.phenotype_threshold,
        recovery_threshold=args.recovery_threshold,
        relation_margin=args.relation_margin,
        min_replicates=args.min_replicates,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
