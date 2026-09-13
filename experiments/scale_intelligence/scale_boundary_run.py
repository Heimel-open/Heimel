#!/usr/bin/env python3
"""Run SCALE-BOUNDARY-12 boundary-excluded scoring ablation."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import mean

from scale_boundary_falsifier import evaluate
from scale_compression_run import harmonic, nuisance_twin
from scale_sweep import (
    EPISODES_PER_FAMILY,
    force_nonzero_majority,
    noisy_blocks,
    sign,
)
from scale_topology_run import (
    DENSE_SCALES,
    FIXED_SUBSTRATE_INVARIANTS,
    TASK_BLOCKS,
    evolve_reflected,
)

REPLICATE_SEEDS = (42042, 43043, 44044, 45045, 46046)
FULL = tuple(range(63))
INTERIOR = tuple(range(16, 47))


def region_accuracy(final: list[float], initial: list[float], region: tuple[int, ...]) -> float:
    target = sign(sum(initial))
    return sum(sign(final[i]) == target for i in region) / len(region)


def region_distance(a: list[float], b: list[float], region: tuple[int, ...]) -> float:
    return mean(abs(a[i] - b[i]) for i in region)


def efficiency_probe_dual(scale: int, seed: int, block: int) -> dict[str, float]:
    rng = random.Random(seed + block * 100000)
    dec = {"full": [], "interior": []}
    comp = {"full": [], "interior": []}

    for _ in range(EPISODES_PER_FAMILY):
        initial = force_nonzero_majority(noisy_blocks(rng, block), rng)
        twin = nuisance_twin(initial, rng)
        final = evolve_reflected(initial, scale)
        twin_final = evolve_reflected(twin, scale)

        for name, region in (("full", FULL), ("interior", INTERIOR)):
            dec[name].append(
                0.5
                * (
                    region_accuracy(final, initial, region)
                    + region_accuracy(twin_final, twin, region)
                )
            )
            initial_distance = region_distance(initial, twin, region)
            final_distance = region_distance(final, twin_final, region)
            if initial_distance <= 0.0:
                comp[name].append(0.0)
            else:
                comp[name].append(
                    max(0.0, min(1.0, 1.0 - final_distance / initial_distance))
                )

    out = {}
    for name in ("full", "interior"):
        target_decodability = mean(dec[name])
        nuisance_compression = mean(comp[name])
        out[f"{name}_target_decodability"] = target_decodability
        out[f"{name}_nuisance_compression"] = nuisance_compression
        out[f"{name}_information_efficiency"] = harmonic(
            target_decodability, nuisance_compression
        )
    return out


def capability_probe_dual(scale: int, seed: int, block: int) -> dict[str, float]:
    unrotated_rng = random.Random(seed + block * 100000 + 1000000)
    rotated_rng = random.Random(seed + block * 100000 + 2000000)
    scores = {"full": [], "interior": []}

    for _ in range(EPISODES_PER_FAMILY):
        initial = force_nonzero_majority(
            noisy_blocks(unrotated_rng, block), unrotated_rng
        )
        final = evolve_reflected(initial, scale)
        for name, region in (("full", FULL), ("interior", INTERIOR)):
            scores[name].append(region_accuracy(final, initial, region))

    for _ in range(EPISODES_PER_FAMILY):
        rotation = rotated_rng.randrange(block)
        initial = force_nonzero_majority(
            noisy_blocks(rotated_rng, block, rotation=rotation), rotated_rng
        )
        final = evolve_reflected(initial, scale)
        for name, region in (("full", FULL), ("interior", INTERIOR)):
            scores[name].append(region_accuracy(final, initial, region))

    return {
        "full_capability": mean(scores["full"]),
        "interior_capability": mean(scores["interior"]),
    }


def run_experiment() -> dict[str, object]:
    trials = []
    for block in TASK_BLOCKS:
        for scale in DENSE_SCALES:
            for replicate, seed in enumerate(REPLICATE_SEEDS):
                efficiency = efficiency_probe_dual(scale, seed, block)
                capability = capability_probe_dual(scale, seed, block)
                trials.append(
                    {
                        "task_block": block,
                        "interaction_scale": scale,
                        "replicate": replicate,
                        "seed": seed,
                        "non_geometry_invariants": dict(FIXED_SUBSTRATE_INVARIANTS),
                        **{k: float(v) for k, v in efficiency.items()},
                        **{k: float(v) for k, v in capability.items()},
                    }
                )

    return {
        "protocol": "SCALE-BOUNDARY-12",
        "canonical_base": "6fce414ddff6e503d8c7ccdccd560eba75b63b48",
        "task_blocks": list(TASK_BLOCKS),
        "scales": list(DENSE_SCALES),
        "replicate_seeds": list(REPLICATE_SEEDS),
        "episodes_per_probe_stream": EPISODES_PER_FAMILY,
        "scoring_regions": {
            "full": [FULL[0], FULL[-1], len(FULL)],
            "interior": [INTERIOR[0], INTERIOR[-1], len(INTERIOR)],
        },
        "scoring_intervention_only": True,
        "fixed_substrate_invariants": dict(FIXED_SUBSTRATE_INVARIANTS),
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_boundary_12_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
