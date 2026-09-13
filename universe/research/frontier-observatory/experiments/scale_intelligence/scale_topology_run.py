#!/usr/bin/env python3
"""Run SCALE-TOPOLOGY-11 on a reflected-line substrate."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import mean

from scale_compression_run import harmonic, nuisance_twin
from scale_peak_falsifier import evaluate
from scale_sweep import (
    EPISODES_PER_FAMILY,
    INVARIANTS,
    NODES,
    NOISE_P,
    ROUNDS,
    digest,
    force_nonzero_majority,
    majority_accuracy,
    noisy_blocks,
)

TASK_BLOCKS = (5, 9, 13)
DENSE_SCALES = tuple(range(4, 16))
REPLICATE_SEEDS = (37037, 38038, 39039, 40040, 41041)

TOPOLOGY_SPEC = {
    "kind": "reflected_line",
    "nodes": NODES,
    "endpoints": [0, NODES - 1],
    "address_period": 2 * (NODES - 1),
    "offsets": ["-2s", "-s", "+s", "+2s"],
    "boundary_rule": "r=j mod 2*(N-1); if r>=N use 2*(N-1)-r",
}
FIXED_SUBSTRATE_INVARIANTS = {
    "node_set": INVARIANTS["node_set"],
    "initial_state": INVARIANTS["initial_state"],
    "compute_budget": INVARIANTS["compute_budget"],
    "update_rule": INVARIANTS["update_rule"],
    "topology": digest(TOPOLOGY_SPEC),
}


def reflected_index(index: int) -> int:
    """Mirror an integer address at endpoints 0 and NODES-1."""
    period = 2 * (NODES - 1)
    reflected = index % period
    if reflected >= NODES:
        reflected = period - reflected
    return reflected


def evolve_reflected(values: list[float], scale: int) -> list[float]:
    """Use the frozen mean-message update with reflected-line addressing."""
    state = list(values)
    offsets = (-2 * scale, -scale, scale, 2 * scale)
    for _ in range(ROUNDS):
        state = [
            (
                state[i]
                + sum(state[reflected_index(i + offset)] for offset in offsets)
            )
            / 5.0
            for i in range(NODES)
        ]
    return state


def efficiency_probe(scale: int, seed: int, block: int) -> dict[str, float]:
    rng = random.Random(seed + block * 100000)
    decodability_scores = []
    compression_scores = []

    for _ in range(EPISODES_PER_FAMILY):
        initial = force_nonzero_majority(noisy_blocks(rng, block), rng)
        twin = nuisance_twin(initial, rng)
        final = evolve_reflected(initial, scale)
        twin_final = evolve_reflected(twin, scale)

        decodability_scores.append(
            0.5
            * (
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
                max(
                    0.0,
                    min(1.0, 1.0 - final_distance / initial_distance),
                )
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
    unrotated_rng = random.Random(seed + block * 100000 + 1000000)
    rotated_rng = random.Random(seed + block * 100000 + 2000000)
    scores = []

    for _ in range(EPISODES_PER_FAMILY):
        initial = force_nonzero_majority(
            noisy_blocks(unrotated_rng, block), unrotated_rng
        )
        scores.append(
            majority_accuracy(evolve_reflected(initial, scale), initial)
        )

    for _ in range(EPISODES_PER_FAMILY):
        rotation = rotated_rng.randrange(block)
        initial = force_nonzero_majority(
            noisy_blocks(rotated_rng, block, rotation=rotation), rotated_rng
        )
        scores.append(
            majority_accuracy(evolve_reflected(initial, scale), initial)
        )

    return mean(scores)


def run_experiment() -> dict[str, object]:
    trials = []
    for block in TASK_BLOCKS:
        for scale in DENSE_SCALES:
            for replicate, seed in enumerate(REPLICATE_SEEDS):
                efficiency = efficiency_probe(scale, seed, block)
                trials.append(
                    {
                        "task_block": block,
                        "interaction_scale": scale,
                        "replicate": replicate,
                        "seed": seed,
                        "non_geometry_invariants": dict(
                            FIXED_SUBSTRATE_INVARIANTS
                        ),
                        "target_decodability": float(
                            efficiency["target_decodability"]
                        ),
                        "nuisance_compression": float(
                            efficiency["nuisance_compression"]
                        ),
                        "information_efficiency": float(
                            efficiency["information_efficiency"]
                        ),
                        "capability": float(
                            capability_probe(scale, seed, block)
                        ),
                    }
                )

    return {
        "protocol": "SCALE-TOPOLOGY-11",
        "canonical_base": "6062231d1ee95348cf3dd53aad576d80c925dbc3",
        "task_blocks": list(TASK_BLOCKS),
        "scales": list(DENSE_SCALES),
        "replicate_seeds": list(REPLICATE_SEEDS),
        "episodes_per_probe_stream": EPISODES_PER_FAMILY,
        "topology": TOPOLOGY_SPEC,
        "fixed_substrate_invariants": dict(FIXED_SUBSTRATE_INVARIANTS),
        "peak_rule": "reuse SCALE-PEAK-10 evaluator unchanged: exact per-replicate argmax, arithmetic mean exact ties, median of five replicate peaks",
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_topology_11_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
