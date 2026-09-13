#!/usr/bin/env python3
"""Run SCALE-RELEVANCE-06 on the frozen scale-sweep substrate."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import mean

from scale_relevance_falsifier import evaluate
from scale_sweep import (
    EPISODES_PER_FAMILY,
    INVARIANTS,
    SCALES,
    SEGMENT_BLOCK,
    evolve,
    force_nonzero_majority,
    noisy_blocks,
    run_replicate,
    sign,
)

REPLICATE_SEEDS = (12012, 13013, 14014, 15015, 16016)


def pairwise_auc(support: list[float], counter: list[float]) -> float:
    """Probability a support node retains a stronger target-aligned state."""
    if not support or not counter:
        return 0.5
    wins = 0.0
    total = 0
    for a in support:
        for b in counter:
            total += 1
            if a > b:
                wins += 1.0
            elif a == b:
                wins += 0.5
    return wins / total


def task_relevant_episode(initial: list[float], final: list[float]) -> tuple[float, float]:
    target = sign(sum(initial))
    aligned = [target * value for value in final]
    support = [aligned[i] for i, value in enumerate(initial) if target * value > 0]
    counter = [aligned[i] for i, value in enumerate(initial) if target * value < 0]
    auc = pairwise_auc(support, counter)
    raw_margin = mean(support) - mean(counter) if support and counter else 0.0
    margin_score = max(0.0, min(1.0, raw_margin / 2.0))
    return auc, margin_score


def task_relevant_for_replicate(scale: int, seed: int) -> tuple[float, float]:
    # Recreate exactly the segmented stream at the start of run_replicate().
    # This is offline instrumentation only and never feeds back into evolution.
    rng = random.Random(seed)
    aucs = []
    margins = []
    for _ in range(EPISODES_PER_FAMILY):
        initial = force_nonzero_majority(noisy_blocks(rng, SEGMENT_BLOCK), rng)
        final = evolve(initial, scale)
        auc, margin = task_relevant_episode(initial, final)
        aucs.append(auc)
        margins.append(margin)
    return mean(aucs), mean(margins)


def run_experiment() -> dict[str, object]:
    trials = []
    for scale in SCALES:
        for replicate, seed in enumerate(REPLICATE_SEEDS):
            base = run_replicate(scale, seed)
            auc, margin = task_relevant_for_replicate(scale, seed)
            trials.append(
                {
                    "interaction_scale": scale,
                    "replicate": replicate,
                    "seed": seed,
                    "invariants": dict(INVARIANTS),
                    "capability": 0.5 * (
                        float(base["task_success"]) + float(base["cross_context_transfer"])
                    ),
                    "integration": float(base["distributed_integration"]),
                    "task_relevant_auc": auc,
                    "task_relevant_margin": margin,
                    "base_metrics": base,
                }
            )

    return {
        "protocol": "SCALE-RELEVANCE-06",
        "prior": "SCALE-ORDER-05 falsified raw-local-differentiation explanation",
        "replicate_seeds": list(REPLICATE_SEEDS),
        "scales": list(SCALES),
        "episodes_per_family": EPISODES_PER_FAMILY,
        "instrumentation": {
            "capability": "mean(task_success, cross_context_transfer)",
            "task_relevant_auc": "within each episode, probability that a node whose initial evidence supports the correct global target has a larger target-aligned final state than a node whose evidence opposes it; ties score 0.5",
            "task_relevant_margin": "positive mean target-aligned support-minus-counterevidence final-state margin divided by the initial maximum separation of 2",
            "integration": "existing distributed_integration",
        },
        "invariants": dict(INVARIANTS),
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_relevance_06_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
