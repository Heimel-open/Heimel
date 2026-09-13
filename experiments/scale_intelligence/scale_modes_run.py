#!/usr/bin/env python3
"""Run SCALE-MODES-18."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np

from scale_boundary_dynamics_run import CONDITION_INVARIANTS
from scale_correlation_run import correlated_blocks
from scale_modes_falsifier import CONDITIONS, SCALES, TASKS, evaluate
from scale_sweep import EPISODES_PER_FAMILY, NODES, ROUNDS, force_nonzero_majority, noisy_blocks

INTERIOR = np.arange(16, 47)
REPLICATE_SEEDS = (72072, 73073, 74074, 75075, 76076)


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


def probe(
    episodes: np.ndarray,
    a3: np.ndarray,
    u: np.ndarray,
    sigma: np.ndarray,
    vt: np.ndarray,
    svd_error: float,
):
    mu = episodes.mean(axis=1)
    target = np.where(mu >= 0.0, 1.0, -1.0)
    residual = episodes - mu[:, None]

    final = episodes @ a3.T
    residual_final_c = residual @ a3[INTERIOR, :].T
    capability = float(np.mean(final[:, INTERIOR] * target[:, None] >= 0.0))

    coeff = residual @ vt.T
    modal = (
        coeff[:, :, None]
        * sigma[None, :, None]
        * u.T[None, :, :]
    )
    aligned = modal * target[:, None, None]
    per_mode_harm = np.mean(np.minimum(aligned, 0.0) ** 2, axis=2)
    total_harm = per_mode_harm.sum(axis=1)
    mu2 = mu * mu
    predictor = np.divide(
        mu2,
        mu2 + total_harm,
        out=np.zeros_like(mu2),
        where=(mu2 + total_harm) > 0,
    )

    denom2 = np.sum(per_mode_harm ** 2, axis=1)
    effective_count = np.divide(
        total_harm ** 2,
        denom2,
        out=np.zeros_like(total_harm),
        where=denom2 > 0,
    )
    sorted_harm = np.sort(per_mode_harm, axis=1)
    top1 = sorted_harm[:, -1]
    top3 = sorted_harm[:, -3:].sum(axis=1)
    top1_share = np.divide(
        top1, total_harm, out=np.zeros_like(top1), where=total_harm > 0
    )
    top3_share = np.divide(
        top3, total_harm, out=np.zeros_like(top3), where=total_harm > 0
    )

    modal_reconstruction = modal.sum(axis=1)
    modal_error = float(np.max(np.abs(modal_reconstruction - residual_final_c)))
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
        "mode_harm_target_fraction": float(np.mean(predictor)),
        "capability": capability,
        "effective_harmful_mode_count": float(np.mean(effective_count)),
        "top1_harmful_share": float(np.mean(top1_share)),
        "top3_harmful_share": float(np.mean(top3_share)),
        "svd_reconstruction_max_error": svd_error,
        "modal_output_reconstruction_max_error": modal_error,
        "state_decomposition_max_error": state_error,
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
        "protocol": "SCALE-MODES-18",
        "canonical_base": "ec8a4cfe20a614e11d98330fbd0c9a66c8963d98",
        "preregistration_sha": "05965bda3a9caccbb6977b89858f45c2cb705799",
        "tasks": list(TASKS),
        "scales": list(SCALES),
        "replicate_seeds": list(REPLICATE_SEEDS),
        "episodes_per_capability_stream": EPISODES_PER_FAMILY,
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_modes_18_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
