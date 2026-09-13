#!/usr/bin/env python3
"""Run SCALE-GEOMETRY-09 on the frozen ring substrate."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import mean

from scale_compression_run import harmonic, nuisance_twin
from scale_geometry_falsifier import evaluate
from scale_sweep import (
    EPISODES_PER_FAMILY,
    INVARIANTS,
    NODES,
    NOISE_P,
    SCALES,
    evolve,
    force_nonzero_majority,
    majority_accuracy,
    noisy_blocks,
)

TASK_BLOCKS = (5, 9, 13)
REPLICATE_SEEDS = (27027, 28028, 29029, 30030, 31031)
NON_GEOMETRY_INVARIANTS = {
    key: value for key, value in INVARIANTS.items() if key != "taskset"
}


def efficiency_probe(scale: int, seed: int, block: int) -> dict[str, float]:
    rng = random.Random(seed + block * 100000)
    decodability_scores = []
    compression_scores = []

    for _ in range(EPISODES_PER_FAMILY):
        initial = force_nonzero_majority(noisy_blocks(rng, block), rng)
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
            compression_scores.append(
                max(0.0, min(1.0, 1.0 - final_distance / initial_distance))
            )

    target_decodability = mean(decodability_scores)
    nuisance_compression = mean(compression_scores)
    return {
        "target_decodability": target_decodability,
        "nuisance_compression": nuisance_compression,
        "information_efficiency": harmonic(
            target_decodability, nuisance_compression
        ),
    }


def capability_probe(scale: int, seed: int, block: int) -> float:
    # Separate deterministic RNG domains keep capability independent of the
    # efficiency episode stream.
    unrotated_rng = random.Random(seed + block * 100000 + 1000000)
    rotated_rng = random.Random(seed + block * 100000 + 2000000)
    scores = []

    for _ in range(EPISODES_PER_FAMILY):
        initial = force_nonzero_majority(noisy_blocks(unrotated_rng, block), unrotated_rng)
        scores.append(majority_accuracy(evolve(initial, scale), initial))

    for _ in range(EPISODES_PER_FAMILY):
        rotation = rotated_rng.randrange(block)
        initial = force_nonzero_majority(
            noisy_blocks(rotated_rng, block, rotation=rotation), rotated_rng
        )
        scores.append(majority_accuracy(evolve(initial, scale), initial))

    return mean(scores)


def run_experiment() -> dict[str, object]:
    trials = []
    for block in TASK_BLOCKS:
        for scale in SCALES:
            for replicate, seed in enumerate(REPLICATE_SEEDS):
                efficiency = efficiency_probe(scale, seed, block)
                trials.append(
                    {
                        "task_block": block,
                        "interaction_scale": scale,
                        "replicate": replicate,
                        "seed": seed,
                        "non_geometry_invariants": dict(NON_GEOMETRY_INVARIANTS),
                        "target_decodability": float(efficiency["target_decodability"]),
                        "nuisance_compression": float(efficiency["nuisance_compression"]),
                        "information_efficiency": float(efficiency["information_efficiency"]),
                        "capability": float(capability_probe(scale, seed, block)),
                    }
                )

    return {
        "protocol": "SCALE-GEOMETRY-09",
        "canonical_base": "15f04e58869b006cc16e8395181eafe3b0e2b40a",
        "preregistration_sha": "9dc82306d3515405cf662c0fd9f1640da20710e9",
        "task_blocks": list(TASK_BLOCKS),
        "scales": list(SCALES),
        "replicate_seeds": list(REPLICATE_SEEDS),
        "episodes_per_probe_stream": EPISODES_PER_FAMILY,
        "frozen_substrate": {
            "nodes": NODES,
            "noise_p": NOISE_P,
            "non_geometry_invariants": dict(NON_GEOMETRY_INVARIANTS),
        },
        "intervention": "segmented task block size only",
        "efficiency_probe": "target decodability plus nuisance-permutation compression; harmonic joint score",
        "capability_probe": "independent unrotated and randomly rotated geometry-matched majority streams",
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_geometry_09_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
