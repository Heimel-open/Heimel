#!/usr/bin/env python3
"""Run SCALE-INTERFERENCE-19."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

import numpy as np

from scale_boundary_dynamics_run import CONDITION_INVARIANTS
from scale_correlation_run import correlated_blocks
from scale_interference_falsifier import CONDITIONS, SCALES, TASKS, evaluate
from scale_sweep import EPISODES_PER_FAMILY, NODES, ROUNDS, force_nonzero_majority, noisy_blocks

INTERIOR = np.arange(16, 47)
REPLICATE_SEEDS = (77077, 78078, 79079, 80080, 81081)
SCRAMBLES = 16


def reflected_index(index: int) -> int:
    period = 2 * (NODES - 1)
    r = index % period
    return period - r if r >= NODES else r


def one_round_matrix(scale: int, condition: str) -> np.ndarray:
    a = np.zeros((NODES, NODES), dtype=float)
    offsets = (-2 * scale, -scale, scale, 2 * scale)
    for i in range(NODES):
        a[i, i] += 0.2
        for offset in offsets:
            j = i + offset
            if condition == "reflected":
                j = reflected_index(j)
            elif not 0 <= j < NODES:
                j = i
            a[i, j] += 0.2
    return a


def task_params(task_id: str):
    if task_id.startswith("seg_b"):
        return "segmented", int(task_id.split("b")[1]), None
    _, bpart, lpart = task_id.split("_")
    return "markov", int(bpart[1:]), int(lpart[1:])


def episode_set(seed: int, task_id: str) -> np.ndarray:
    family, block, corr = task_params(task_id)
    corr_term = 0 if corr is None else corr * 1000
    base = seed + block * 100000 + corr_term
    unrotated_rng = random.Random(base + 3000000)
    rotated_rng = random.Random(base + 4000000)
    episodes = []

    for _ in range(EPISODES_PER_FAMILY):
        if family == "segmented":
            x = force_nonzero_majority(noisy_blocks(unrotated_rng, block), unrotated_rng)
        else:
            x = correlated_blocks(unrotated_rng, block, corr, rotation=0)
        episodes.append(x)

    for _ in range(EPISODES_PER_FAMILY):
        rotation = rotated_rng.randrange(block)
        if family == "segmented":
            x = force_nonzero_majority(
                noisy_blocks(rotated_rng, block, rotation=rotation), rotated_rng
            )
        else:
            x = correlated_blocks(rotated_rng, block, corr, rotation=rotation)
        episodes.append(x)

    return np.asarray(episodes, dtype=float)


def mask_seed(seed: int, task_id: str, scale: int, condition: str) -> int:
    payload = f"SCALE-INTERFERENCE-19|{seed}|{task_id}|{scale}|{condition}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big", signed=False)


def probe(
    episodes: np.ndarray,
    a3: np.ndarray,
    u: np.ndarray,
    sigma: np.ndarray,
    vt: np.ndarray,
    svd_error: float,
    scramble_seed: int,
):
    mu = episodes.mean(axis=1)
    target = np.where(mu >= 0.0, 1.0, -1.0)
    residual = episodes - mu[:, None]

    final = episodes @ a3.T
    residual_final_c = residual @ a3[INTERIOR, :].T
    native_capability = float(np.mean(final[:, INTERIOR] * target[:, None] >= 0.0))

    coeff = residual @ vt.T
    modal = (
        coeff[:, :, None]
        * sigma[None, :, None]
        * u.T[None, :, :]
    )
    native_residual_c = modal.sum(axis=1)

    rng = np.random.default_rng(scramble_seed)
    masks = rng.choice(
        np.array([-1.0, 1.0]),
        size=(SCRAMBLES, episodes.shape[0], modal.shape[1]),
    )
    scrambled_residual_c = np.einsum(
        "qem,emc->qec",
        masks,
        modal,
        optimize=True,
    )
    scrambled_final_c = mu[None, :, None] + scrambled_residual_c
    scrambled_by_mask = np.mean(
        scrambled_final_c * target[None, :, None] >= 0.0,
        axis=(1, 2),
    )
    scrambled_capability = float(np.mean(scrambled_by_mask))

    native_power = np.sum(native_residual_c ** 2, axis=1)
    scrambled_power = np.sum(scrambled_residual_c ** 2, axis=2)
    energy_error = float(
        np.max(np.abs(scrambled_power - native_power[None, :]))
    )

    modal_reconstruction = modal.sum(axis=1)
    modal_error = float(
        np.max(np.abs(modal_reconstruction - residual_final_c))
    )
    state_error = float(
        np.max(
            np.abs(
                final
                - (
                    mu[:, None]
                    + residual @ a3.T
                )
            )
        )
    )

    return {
        "native_capability": native_capability,
        "scrambled_capability": scrambled_capability,
        "scrambled_capability_sd": float(np.std(scrambled_by_mask)),
        "svd_reconstruction_max_error": svd_error,
        "modal_output_reconstruction_max_error": modal_error,
        "state_decomposition_max_error": state_error,
        "scramble_energy_max_error": energy_error,
    }


def run_experiment():
    q = np.eye(NODES) - np.ones((NODES, NODES)) / NODES
    operators = {}
    decompositions = {}

    for condition in CONDITIONS:
        for scale in SCALES:
            a = one_round_matrix(scale, condition)
            a3 = np.linalg.matrix_power(a, ROUNDS)
            b = a3[INTERIOR, :] @ q
            u, sigma, vt = np.linalg.svd(b, full_matrices=False)
            svd_error = float(np.max(np.abs(b - (u * sigma) @ vt)))
            operators[(condition, scale)] = a3
            decompositions[(condition, scale)] = (u, sigma, vt, svd_error)

    trials = []
    for task_id in TASKS:
        for replicate, seed in enumerate(REPLICATE_SEEDS):
            episodes = episode_set(seed, task_id)
            for scale in SCALES:
                for condition in CONDITIONS:
                    u, sigma, vt, svd_error = decompositions[(condition, scale)]
                    metrics = probe(
                        episodes,
                        operators[(condition, scale)],
                        u,
                        sigma,
                        vt,
                        svd_error,
                        mask_seed(seed, task_id, scale, condition),
                    )
                    trials.append(
                        {
                            "boundary_condition": condition,
                            "task_id": task_id,
                            "interaction_scale": scale,
                            "replicate": replicate,
                            "seed": seed,
                            "condition_invariants": dict(CONDITION_INVARIANTS[condition]),
                            **metrics,
                        }
                    )

    return {
        "protocol": "SCALE-INTERFERENCE-19",
        "canonical_base": "9210f5871c6040d4158112f95a2ed5ebae4dbcef",
        "preregistration_sha": "fef3df4ea98e70d606c5c99ea0a3384c6c23e9c1",
        "tasks": list(TASKS),
        "scales": list(SCALES),
        "replicate_seeds": list(REPLICATE_SEEDS),
        "scrambles_per_trial": SCRAMBLES,
        "episodes_per_capability_stream": EPISODES_PER_FAMILY,
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_interference_19_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
