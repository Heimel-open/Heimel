#!/usr/bin/env python3
"""Run SCALE-ORDER-05 on the frozen scale-sweep substrate."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from statistics import mean

from scale_order_falsifier import evaluate
from scale_sweep import (
    EPISODES_PER_FAMILY,
    INVARIANTS,
    NODES,
    NOISE_P,
    SCALES,
    SEGMENT_BLOCK,
    evolve,
    force_nonzero_majority,
    noisy_blocks,
    run_replicate,
)

REPLICATE_SEEDS = (7007, 8008, 9009, 10010, 11011)


def local_structure_retention(initial: list[float], final: list[float]) -> float:
    """Retained local structure after removing the shared/global component.

    Positive centered correlation rewards preservation of which nodes differ from
    the global mean. The amplitude term forces the score toward zero when local
    distinctions collapse even if correlation remains numerically defined.
    """
    initial_mean = mean(initial)
    final_mean = mean(final)
    x = [value - initial_mean for value in initial]
    y = [value - final_mean for value in final]

    x_energy = sum(value * value for value in x)
    y_energy = sum(value * value for value in y)
    if x_energy <= 0.0 or y_energy <= 0.0:
        return 0.0

    corr = sum(a * b for a, b in zip(x, y)) / math.sqrt(x_energy * y_energy)
    amplitude_retention = min(1.0, math.sqrt(y_energy / x_energy))
    return max(0.0, min(1.0, corr * amplitude_retention))


def differentiation_for_replicate(scale: int, seed: int) -> float:
    # Recreate exactly the segmented episode stream used at the start of
    # scale_sweep.run_replicate(). This is offline instrumentation only; it
    # does not alter the substrate or feed information back into evolution.
    rng = random.Random(seed)
    scores = []
    for _ in range(EPISODES_PER_FAMILY):
        initial = force_nonzero_majority(noisy_blocks(rng, SEGMENT_BLOCK), rng)
        final = evolve(initial, scale)
        scores.append(local_structure_retention(initial, final))
    return mean(scores)


def harmonic_balance(integration: float, differentiation: float) -> float:
    total = integration + differentiation
    if total <= 0.0:
        return 0.0
    return 2.0 * integration * differentiation / total


def run_experiment() -> dict[str, object]:
    trials = []
    for scale in SCALES:
        for replicate, seed in enumerate(REPLICATE_SEEDS):
            base = run_replicate(scale, seed)
            integration = float(base["distributed_integration"])
            differentiation = differentiation_for_replicate(scale, seed)
            capability = 0.5 * (
                float(base["task_success"]) + float(base["cross_context_transfer"])
            )
            trials.append(
                {
                    "interaction_scale": scale,
                    "replicate": replicate,
                    "seed": seed,
                    "invariants": dict(INVARIANTS),
                    "integration": integration,
                    "differentiation": differentiation,
                    "capability": capability,
                    "balance": harmonic_balance(integration, differentiation),
                    "base_metrics": base,
                }
            )

    return {
        "protocol": "SCALE-ORDER-05",
        "hypothesis": "capability peaks between fragmentation and over-integration",
        "replicate_seeds": list(REPLICATE_SEEDS),
        "scales": list(SCALES),
        "episodes_per_family": EPISODES_PER_FAMILY,
        "instrumentation": {
            "integration": "existing distributed_integration metric",
            "differentiation": "positive centered input/final correlation times retained centered amplitude",
            "capability": "mean(task_success, cross_context_transfer); excludes integration and differentiation",
            "balance": "harmonic mean(integration, differentiation)",
        },
        "frozen_substrate": {
            "nodes": NODES,
            "segmented_block": SEGMENT_BLOCK,
            "noise_p": NOISE_P,
            "invariants": dict(INVARIANTS),
        },
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_order_05_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
