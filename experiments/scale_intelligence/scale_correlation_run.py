#!/usr/bin/env python3
"""Run SCALE-CORRELATION-16."""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from statistics import mean

from scale_boundary_dynamics_run import (
    CONDITION_INVARIANTS,
    EVOLVERS,
)
from scale_boundary_run import INTERIOR, region_accuracy, region_distance
from scale_compression_run import harmonic, nuisance_twin
from scale_correlation_falsifier import (
    BLOCKS,
    CORRELATION_LENGTHS,
    SCALES,
    evaluate,
)
from scale_sweep import EPISODES_PER_FAMILY, NODES, NOISE_P, force_nonzero_majority

REPLICATE_SEEDS = (62062, 63063, 64064, 65065, 66066)


def correlated_blocks(
    rng: random.Random,
    block: int,
    correlation_length: int,
    rotation: int = 0,
    return_latent: bool = False,
):
    rho = math.exp(-block / correlation_length)
    p_same = (1.0 + rho) / 2.0
    max_source = (NODES - 1) + rotation
    block_count = max_source // block + 1
    latent = [rng.choice((-1, 1))]
    for _ in range(1, block_count):
        latent.append(latent[-1] if rng.random() < p_same else -latent[-1])

    values = []
    for i in range(NODES):
        source = i + rotation
        value = latent[source // block]
        if rng.random() < NOISE_P:
            value *= -1
        values.append(float(value))
    values = force_nonzero_majority(values, rng)
    if return_latent:
        return values, latent, rho
    return values


def efficiency_probe_pair(scale, seed, block, correlation_length):
    rng = random.Random(seed + block * 100000 + correlation_length * 1000)
    dec = {condition: [] for condition in EVOLVERS}
    comp = {condition: [] for condition in EVOLVERS}
    latent_pairs = []

    for _ in range(EPISODES_PER_FAMILY):
        initial, latent, rho = correlated_blocks(
            rng, block, correlation_length, return_latent=True
        )
        twin = nuisance_twin(initial, rng)
        latent_pairs.extend(zip(latent[:-1], latent[1:]))
        for condition, evolve in EVOLVERS.items():
            final = evolve(initial, scale)
            twin_final = evolve(twin, scale)
            dec[condition].append(
                0.5
                * (
                    region_accuracy(final, initial, INTERIOR)
                    + region_accuracy(twin_final, twin, INTERIOR)
                )
            )
            initial_distance = region_distance(initial, twin, INTERIOR)
            final_distance = region_distance(final, twin_final, INTERIOR)
            comp[condition].append(
                0.0
                if initial_distance <= 0
                else max(0.0, min(1.0, 1.0 - final_distance / initial_distance))
            )

    same_minus_diff = (
        mean(a * b for a, b in latent_pairs) if latent_pairs else float("nan")
    )
    l_hat = (
        -block / math.log(same_minus_diff)
        if 0.0 < same_minus_diff < 1.0
        else None
    )
    return {
        condition: {
            "target_decodability": mean(dec[condition]),
            "nuisance_compression": mean(comp[condition]),
            "information_efficiency": harmonic(
                mean(dec[condition]), mean(comp[condition])
            ),
        }
        for condition in EVOLVERS
    }, {
        "configured_rho": rho,
        "latent_adjacent_correlation_hat": same_minus_diff,
        "latent_correlation_length_hat": l_hat,
    }


def capability_probe_pair(scale, seed, block, correlation_length):
    unrotated_rng = random.Random(
        seed + block * 100000 + correlation_length * 1000 + 1000000
    )
    rotated_rng = random.Random(
        seed + block * 100000 + correlation_length * 1000 + 2000000
    )
    scores = {condition: [] for condition in EVOLVERS}

    for _ in range(EPISODES_PER_FAMILY):
        initial = correlated_blocks(
            unrotated_rng, block, correlation_length, rotation=0
        )
        for condition, evolve in EVOLVERS.items():
            scores[condition].append(
                region_accuracy(evolve(initial, scale), initial, INTERIOR)
            )

    for _ in range(EPISODES_PER_FAMILY):
        rotation = rotated_rng.randrange(block)
        initial = correlated_blocks(
            rotated_rng, block, correlation_length, rotation=rotation
        )
        for condition, evolve in EVOLVERS.items():
            scores[condition].append(
                region_accuracy(evolve(initial, scale), initial, INTERIOR)
            )

    return {condition: mean(values) for condition, values in scores.items()}


def run_experiment():
    trials = []
    generator_diagnostics = {}
    for block in BLOCKS:
        generator_diagnostics[block] = {}
        for corr in CORRELATION_LENGTHS:
            generator_diagnostics[block][corr] = []
            for scale in SCALES:
                for replicate, seed in enumerate(REPLICATE_SEEDS):
                    efficiency, generator = efficiency_probe_pair(
                        scale, seed, block, corr
                    )
                    capability = capability_probe_pair(
                        scale, seed, block, corr
                    )
                    if scale == SCALES[0]:
                        generator_diagnostics[block][corr].append(generator)
                    for condition in EVOLVERS:
                        trials.append({
                            "boundary_condition": condition,
                            "nominal_block": block,
                            "correlation_length": corr,
                            "interaction_scale": scale,
                            "replicate": replicate,
                            "seed": seed,
                            "condition_invariants": dict(CONDITION_INVARIANTS[condition]),
                            "target_decodability": float(
                                efficiency[condition]["target_decodability"]
                            ),
                            "nuisance_compression": float(
                                efficiency[condition]["nuisance_compression"]
                            ),
                            "information_efficiency": float(
                                efficiency[condition]["information_efficiency"]
                            ),
                            "capability": float(capability[condition]),
                        })
    return {
        "protocol": "SCALE-CORRELATION-16",
        "canonical_base": "00ef323fe1e712ea3e139cc9c39b0224f2e9c8e2",
        "preregistration_sha": "7e14740f36429f48f8f93054f50febb7c27ef9db",
        "nominal_blocks": list(BLOCKS),
        "correlation_lengths": list(CORRELATION_LENGTHS),
        "scales": list(SCALES),
        "replicate_seeds": list(REPLICATE_SEEDS),
        "episodes_per_probe_stream": EPISODES_PER_FAMILY,
        "generator_diagnostics": generator_diagnostics,
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_correlation_16_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
