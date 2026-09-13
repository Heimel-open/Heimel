#!/usr/bin/env python3
"""Run SCALE-PAIR-PHASE-22."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

import numpy as np

from scale_pair_phase_falsifier import evaluate
from scale_sweep import (
    EPISODES_PER_FAMILY,
    NODES,
    ROUNDS,
    force_nonzero_majority,
    noisy_blocks,
)

INTERIOR = np.arange(16, 47)
BLOCK = 13
SCALES = (7, 13)
FRESH_SEEDS = (
    97097, 98098, 99099, 100100, 101101,
    102102, 103103, 104104, 105105, 106106,
)
TARGET_PAIR = (6, 7)


def one_round_self_padded(scale: int) -> np.ndarray:
    a = np.zeros((NODES, NODES), dtype=float)
    for i in range(NODES):
        a[i, i] += 0.2
        for offset in (-2 * scale, -scale, scale, 2 * scale):
            j = i + offset
            if not 0 <= j < NODES:
                j = i
            a[i, j] += 0.2
    return a


def episodes(seed: int) -> np.ndarray:
    base = seed + BLOCK * 100000
    unrotated = random.Random(base + 3000000)
    rotated = random.Random(base + 4000000)
    xs = []

    for _ in range(EPISODES_PER_FAMILY):
        xs.append(
            force_nonzero_majority(
                noisy_blocks(unrotated, BLOCK),
                unrotated,
            )
        )

    for _ in range(EPISODES_PER_FAMILY):
        rotation = rotated.randrange(BLOCK)
        xs.append(
            force_nonzero_majority(
                noisy_blocks(rotated, BLOCK, rotation=rotation),
                rotated,
            )
        )

    return np.asarray(xs, dtype=float)


def decompose(scale: int):
    a = one_round_self_padded(scale)
    a3 = np.linalg.matrix_power(a, ROUNDS)
    q = np.eye(NODES) - np.ones((NODES, NODES)) / NODES
    b = a3[INTERIOR, :] @ q
    u, sigma, vt = np.linalg.svd(b, full_matrices=False)
    svd_error = float(np.max(np.abs(b - (u * sigma) @ vt)))
    return a3, u, sigma, vt, svd_error


def modal_state(xs, a3, u, sigma, vt):
    mu = xs.mean(axis=1)
    target = np.where(mu >= 0.0, 1.0, -1.0)
    residual = xs - mu[:, None]
    coeff = residual @ vt.T
    modal = (
        coeff[:, :, None]
        * sigma[None, :, None]
        * u.T[None, :, :]
    )

    final = xs @ a3.T
    native_capability = float(
        np.mean(final[:, INTERIOR] * target[:, None] >= 0.0)
    )
    native_margin = (
        mu[:, None] * target[:, None]
        + modal.sum(axis=1) * target[:, None]
    )
    aligned_modal = modal * target[:, None, None]

    reconstruction_error = max(
        float(
            np.max(
                np.abs(
                    modal.sum(axis=1)
                    - residual @ a3[INTERIOR, :].T
                )
            )
        ),
        float(
            np.max(
                np.abs(
                    final
                    - (
                        mu[:, None]
                        + residual @ a3.T
                    )
                )
            )
        ),
    )
    return native_capability, native_margin, aligned_modal, reconstruction_error


def pair_phase_contrasts(native_margin, aligned_modal):
    native = float(np.mean(native_margin >= 0.0))
    out = np.empty(465, dtype=float)
    pairs = []
    idx = 0

    for j in range(31):
        gj = aligned_modal[:, j, :]
        c_minus_j = float(np.mean(native_margin - 2 * gj >= 0.0))
        for k in range(j + 1, 31):
            gk = aligned_modal[:, k, :]
            c_minus_k = float(np.mean(native_margin - 2 * gk >= 0.0))
            c_minus_both = float(
                np.mean(native_margin - 2 * gj - 2 * gk >= 0.0)
            )

            # (C++ + C--)/2 - (C+- + C-+)/2
            out[idx] = (
                native + c_minus_both - c_minus_k - c_minus_j
            ) / 2.0
            pairs.append((j, k))
            idx += 1

    return pairs, out


def bootstrap_ci(values):
    rng = np.random.default_rng(220022)
    x = np.asarray(values, dtype=float)
    draws = np.empty(20000, dtype=float)
    for i in range(len(draws)):
        draws[i] = rng.choice(x, size=len(x), replace=True).mean()
    return [
        float(np.quantile(draws, 0.025)),
        float(np.quantile(draws, 0.975)),
    ]


def run_experiment():
    operators = {scale: decompose(scale) for scale in SCALES}
    max_error = 0.0
    phase_by_replicate = []
    native_advantages = []
    pairs = None

    for seed in FRESH_SEEDS:
        xs = episodes(seed)
        native = {}
        phase = {}

        for scale in SCALES:
            a3, u, sigma, vt, svd_error = operators[scale]
            n, margin, modal, reconstruction_error = modal_state(
                xs, a3, u, sigma, vt
            )
            max_error = max(
                max_error,
                svd_error,
                reconstruction_error,
            )
            p, contrast = pair_phase_contrasts(margin, modal)
            if pairs is None:
                pairs = p
            elif pairs != p:
                raise RuntimeError("pair order drift")
            native[scale] = n
            phase[scale] = contrast

        native_advantages.append(native[13] - native[7])
        phase_by_replicate.append(phase[13] - phase[7])

    phase_by_replicate = np.asarray(phase_by_replicate)
    mean_phase = phase_by_replicate.mean(axis=0)

    pair_index = {pair: i for i, pair in enumerate(pairs)}
    target_index = pair_index[TARGET_PAIR]
    target_mean = float(mean_phase[target_index])
    target_reps = [
        float(x) for x in phase_by_replicate[:, target_index]
    ]

    other_ge = sum(
        i != target_index and value >= target_mean
        for i, value in enumerate(mean_phase)
    )
    exact_p = (1 + other_ge) / 465.0

    order = np.argsort(mean_phase)[::-1]
    target_rank = int(np.where(order == target_index)[0][0]) + 1

    result = {
        "protocol": "SCALE-PAIR-PHASE-22",
        "canonical_base": "420ca42768d3fd9d638681c70a52f815fd26ef66",
        "preregistration_sha": "cf30b772c04278b9b9e18c0a2380be72d9a9f7cc",
        "pair_count": 465,
        "replicate_count": len(FRESH_SEEDS),
        "fresh_seeds": list(FRESH_SEEDS),
        "target_pair": list(TARGET_PAIR),
        "max_numerical_error": max_error,
        "primary": {
            "target_mean_delta_phase": target_mean,
            "target_replicate_delta_phase": target_reps,
            "target_positive_replicates": sum(x > 0 for x in target_reps),
            "target_bootstrap_95_ci": bootstrap_ci(target_reps),
            "target_rank": target_rank,
            "other_pairs_ge_target": int(other_ge),
            "exact_pair_label_p": exact_p,
        },
        "native_advantage": {
            "replicates": [float(x) for x in native_advantages],
            "mean": float(np.mean(native_advantages)),
            "bootstrap_95_ci": bootstrap_ci(native_advantages),
        },
        "fresh_pair_mean_delta_phase": [
            {
                "pair": list(pair),
                "mean_delta_phase": float(mean_phase[i]),
            }
            for i, pair in enumerate(pairs)
        ],
    }
    result["verdict"] = evaluate(result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="scale_pair_phase_22_result.json",
    )
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
