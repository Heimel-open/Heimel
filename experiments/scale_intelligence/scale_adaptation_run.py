#!/usr/bin/env python3
"""Run SCALE-ADAPTATION-03 with one adaptation enabler: temporal state carryover."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import mean

from scale_adaptation_falsifier import evaluate
from scale_sweep import (
    EPISODES_PER_FAMILY,
    INVARIANTS,
    NODES,
    SCALES,
    counterfactual_pair,
    evolve,
    sign,
)

REPLICATE_SEEDS = (1001, 2002, 3003)
ENABLER = "temporal_state_carryover_with_exact_input_delta"


def adaptation_score(before_final: list[float], after_final: list[float], before: list[float], after: list[float]) -> float:
    before_target = sign(sum(before))
    after_target = sign(sum(after))
    return sum(
        sign(a) == before_target and sign(b) == after_target
        for a, b in zip(before_final, after_final)
    ) / NODES


def run_pair(scale: int, seed: int) -> tuple[float, float]:
    rng = random.Random(seed)
    baseline_scores = []
    carryover_scores = []

    for _ in range(EPISODES_PER_FAMILY):
        before, after = counterfactual_pair(rng)
        before_final = evolve(before, scale)

        # Frozen baseline from SCALE-INTELLIGENCE-01/02: recompute the changed
        # state independently from raw input.
        baseline_after = evolve(after, scale)
        baseline_scores.append(
            adaptation_score(before_final, baseline_after, before, after)
        )

        # The single enabler. Retain the prior evolved scalar state and inject
        # only the exact observed input delta before applying the same evolve()
        # rule for the same number of rounds. No extra channel, round, node,
        # edge, fanout, task information, or model is introduced.
        carryover_initial = [
            before_final[i] + (after[i] - before[i]) for i in range(NODES)
        ]
        carryover_after = evolve(carryover_initial, scale)
        carryover_scores.append(
            adaptation_score(before_final, carryover_after, before, after)
        )

    return mean(baseline_scores), mean(carryover_scores)


def run_experiment() -> dict[str, object]:
    trials = []
    for scale in SCALES:
        for replicate, seed in enumerate(REPLICATE_SEEDS):
            baseline, enabled = run_pair(scale, seed)
            common = {
                "interaction_scale": scale,
                "replicate": replicate,
                "seed": seed,
                "invariants": dict(INVARIANTS),
            }
            trials.append(
                {
                    **common,
                    "condition": "baseline",
                    "counterfactual_adaptation": baseline,
                }
            )
            trials.append(
                {
                    **common,
                    "condition": "temporal_carryover",
                    "counterfactual_adaptation": enabled,
                }
            )

    return {
        "protocol": "SCALE-ADAPTATION-03",
        "base_protocols": ["SCALE-INTELLIGENCE-01", "SCALE-SEPARATION-02"],
        "enabler": ENABLER,
        "replicate_seeds": list(REPLICATE_SEEDS),
        "scales": list(SCALES),
        "episodes_per_scale_replicate": EPISODES_PER_FAMILY,
        "invariants": dict(INVARIANTS),
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_adaptation_03_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
