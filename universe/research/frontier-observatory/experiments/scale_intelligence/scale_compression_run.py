#!/usr/bin/env python3
"""Run SCALE-COMPRESSION-07 on the frozen ring substrate."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import mean

from scale_compression_falsifier import evaluate
from scale_sweep import (
    EPISODES_PER_FAMILY,
    INVARIANTS,
    SCALES,
    SEGMENT_BLOCK,
    evolve,
    force_nonzero_majority,
    majority_accuracy,
    noisy_blocks,
)

REPLICATE_SEEDS = (17017, 18018, 19019, 20020, 21021)


def harmonic(a: float, b: float) -> float:
    if a <= 0.0 or b <= 0.0:
        return 0.0
    return 2.0 * a * b / (a + b)


def nuisance_twin(initial: list[float], rng: random.Random) -> list[float]:
    """Permute node-local evidence while preserving the full multiset and target."""
    twin = list(initial)
    for _ in range(8):
        rng.shuffle(twin)
        if twin != initial:
            return twin
    return twin


def probe_replicate(scale: int, seed: int) -> dict[str, float]:
    rng = random.Random(seed)
    decodability_scores = []
    compression_scores = []

    for _ in range(EPISODES_PER_FAMILY):
        initial = force_nonzero_majority(noisy_blocks(rng, SEGMENT_BLOCK), rng)
        twin = nuisance_twin(initial, rng)
        final = evolve(initial, scale)
        twin_final = evolve(twin, scale)

        decodability_scores.append(
            0.5 * (
                majority_accuracy(final, initial)
                + majority_accuracy(twin_final, twin)
            )
        )

        initial_distance = mean(abs(a - b) for a, b in zip(initial, twin))
        final_distance = mean(abs(a - b) for a, b in zip(final, twin_final))
        if initial_distance <= 0.0:
            compression_scores.append(0.0)
        else:
            retention = final_distance / initial_distance
            compression_scores.append(max(0.0, min(1.0, 1.0 - retention)))

    target_decodability = mean(decodability_scores)
    nuisance_compression = mean(compression_scores)
    return {
        "target_decodability": target_decodability,
        "nuisance_compression": nuisance_compression,
        "sufficient_compression": harmonic(target_decodability, nuisance_compression),
    }


def run_experiment() -> dict[str, object]:
    trials = []
    for scale in SCALES:
        for replicate, seed in enumerate(REPLICATE_SEEDS):
            metrics = probe_replicate(scale, seed)
            trials.append(
                {
                    "interaction_scale": scale,
                    "replicate": replicate,
                    "seed": seed,
                    "invariants": dict(INVARIANTS),
                    **metrics,
                }
            )

    return {
        "protocol": "SCALE-COMPRESSION-07",
        "prior": "SCALE-RELEVANCE-06 falsified preservation of local task-relevant evidence as the scale-8 explanation",
        "replicate_seeds": list(REPLICATE_SEEDS),
        "scales": list(SCALES),
        "episodes_per_scale_replicate": EPISODES_PER_FAMILY,
        "probe": {
            "task": "global-majority decision on segmented inputs",
            "nuisance_intervention": "random permutation of the complete node-value multiset; preserves global sum, target, counts, node set, compute and update rule",
            "target_decodability": "mean node-level target accuracy across original and nuisance twin",
            "nuisance_compression": "one minus final paired mean-absolute state distance divided by initial paired mean-absolute state distance, clipped to [0,1]",
            "sufficient_compression": "harmonic mean(target_decodability, nuisance_compression)",
        },
        "invariants": dict(INVARIANTS),
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_compression_07_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
