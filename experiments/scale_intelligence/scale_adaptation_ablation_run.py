#!/usr/bin/env python3
"""Run the frozen SCALE-ADAPTATION-04 carryover × delta ablation."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import mean

from scale_adaptation_ablation_falsifier import evaluate
from scale_adaptation_run import adaptation_score
from scale_sweep import (
    EPISODES_PER_FAMILY,
    INVARIANTS,
    NODES,
    SCALES,
    counterfactual_pair,
    evolve,
)

REPLICATE_SEEDS = (4004, 5005, 6006)
CONDITIONS = ("baseline", "carryover_only", "delta_only", "joint")


def run_pair(scale: int, seed: int) -> dict[str, float]:
    rng = random.Random(seed)
    scores = {condition: [] for condition in CONDITIONS}

    for _ in range(EPISODES_PER_FAMILY):
        before, after = counterfactual_pair(rng)
        before_final = evolve(before, scale)
        delta = [after[i] - before[i] for i in range(NODES)]

        after_states = {
            "baseline": evolve(after, scale),
            "carryover_only": evolve(before_final, scale),
            "delta_only": evolve(delta, scale),
            "joint": evolve(
                [before_final[i] + delta[i] for i in range(NODES)], scale
            ),
        }
        for condition, after_final in after_states.items():
            scores[condition].append(
                adaptation_score(before_final, after_final, before, after)
            )

    return {condition: mean(values) for condition, values in scores.items()}


def run_experiment() -> dict[str, object]:
    trials = []
    for scale in SCALES:
        for replicate, seed in enumerate(REPLICATE_SEEDS):
            condition_scores = run_pair(scale, seed)
            for condition in CONDITIONS:
                trials.append(
                    {
                        "interaction_scale": scale,
                        "replicate": replicate,
                        "seed": seed,
                        "condition": condition,
                        "invariants": dict(INVARIANTS),
                        "counterfactual_adaptation": condition_scores[condition],
                    }
                )

    return {
        "protocol": "SCALE-ADAPTATION-04",
        "base_protocol": "SCALE-ADAPTATION-03",
        "preregistered_conditions": list(CONDITIONS),
        "replicate_seeds": list(REPLICATE_SEEDS),
        "scales": list(SCALES),
        "episodes_per_scale_replicate": EPISODES_PER_FAMILY,
        "invariants": dict(INVARIANTS),
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_adaptation_04_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
