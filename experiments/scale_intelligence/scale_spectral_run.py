#!/usr/bin/env python3
"""Run SCALE-SPECTRAL-17."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import mean

from scale_boundary_dynamics_run import CONDITION_INVARIANTS, EVOLVERS
from scale_boundary_run import INTERIOR, region_accuracy
from scale_correlation_run import correlated_blocks
from scale_spectral_falsifier import SCALES, TASKS, evaluate
from scale_sweep import EPISODES_PER_FAMILY, NODES, noisy_blocks, force_nonzero_majority

REPLICATE_SEEDS = (67067, 68068, 69069, 70070, 71071)


def _task_params(task_id: str):
    if task_id.startswith("seg_b"):
        return ("segmented", int(task_id.split("b")[1]), None)
    _, bpart, lpart = task_id.split("_")
    return ("markov", int(bpart[1:]), int(lpart[1:]))


def _rngs(seed: int, task_id: str):
    family, block, corr = _task_params(task_id)
    corr_term = 0 if corr is None else corr * 1000
    base = seed + block * 100000 + corr_term
    return random.Random(base + 3000000), random.Random(base + 4000000)


def _initial(rng: random.Random, task_id: str, rotation: int):
    family, block, corr = _task_params(task_id)
    if family == "segmented":
        return force_nonzero_majority(noisy_blocks(rng, block, rotation=rotation), rng)
    return correlated_blocks(rng, block, corr, rotation=rotation)


def _episode_set(seed: int, task_id: str):
    family, block, _ = _task_params(task_id)
    unrotated_rng, rotated_rng = _rngs(seed, task_id)
    episodes = []
    for _ in range(EPISODES_PER_FAMILY):
        episodes.append(_initial(unrotated_rng, task_id, 0))
    for _ in range(EPISODES_PER_FAMILY):
        rotation = rotated_rng.randrange(block)
        episodes.append(_initial(rotated_rng, task_id, rotation))
    return episodes


def _probe(condition: str, scale: int, episodes):
    evolve = EVOLVERS[condition]
    spectral_scores = []
    capability_scores = []
    residual_powers = []
    decomposition_error = 0.0

    for initial in episodes:
        mu = mean(initial)
        residual = [x - mu for x in initial]
        final = evolve(initial, scale)
        residual_final = evolve(residual, scale)

        decomposition_error = max(
            decomposition_error,
            max(abs(a - (mu + r)) for a, r in zip(final, residual_final)),
        )
        residual_power = mean(residual_final[i] ** 2 for i in INTERIOR)
        mu2 = mu * mu
        spectral_scores.append(
            1.0 if residual_power <= 0.0 and mu2 > 0.0
            else (0.0 if mu2 <= 0.0 else mu2 / (mu2 + residual_power))
        )
        residual_powers.append(residual_power)
        capability_scores.append(region_accuracy(final, initial, INTERIOR))

    return {
        "spectral_target_fraction": mean(spectral_scores),
        "capability": mean(capability_scores),
        "residual_power": mean(residual_powers),
        "decomposition_max_error": decomposition_error,
    }


def run_experiment():
    trials = []
    for task_id in TASKS:
        for replicate, seed in enumerate(REPLICATE_SEEDS):
            episodes = _episode_set(seed, task_id)
            for scale in SCALES:
                for condition in EVOLVERS:
                    metrics = _probe(condition, scale, episodes)
                    trials.append({
                        "boundary_condition": condition,
                        "task_id": task_id,
                        "interaction_scale": scale,
                        "replicate": replicate,
                        "seed": seed,
                        "condition_invariants": dict(CONDITION_INVARIANTS[condition]),
                        **{k: float(v) for k, v in metrics.items()},
                    })
    return {
        "protocol": "SCALE-SPECTRAL-17",
        "canonical_base": "ac7079c26da8fdbdc655eaf3c609df3ae6bc400e",
        "preregistration_sha": "f73ccd1beafb5946653766fae8c96c5f70c44f1f",
        "tasks": list(TASKS),
        "scales": list(SCALES),
        "replicate_seeds": list(REPLICATE_SEEDS),
        "episodes_per_capability_stream": EPISODES_PER_FAMILY,
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_spectral_17_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
