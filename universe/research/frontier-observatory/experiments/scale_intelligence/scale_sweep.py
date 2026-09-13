#!/usr/bin/env python3
"""Run the preregistered CPU-only scale sweep on a fixed ring substrate.

The intervention changes only interaction_scale. Node count, latent topology,
message fanout, update rule, number of rounds, task generator, episode count,
and evaluation rules remain fixed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from statistics import mean
from typing import Iterable

from scale_phase_falsifier import evaluate

NODES = 63
SCALES = (1, 2, 4, 8, 16)
REPLICATE_SEEDS = (101, 202, 303)
ROUNDS = 3
FANOUT = 4
EPISODES_PER_FAMILY = 256
SEGMENT_BLOCK = 9
TRANSFER_BLOCK = 7
NOISE_P = 0.10


def digest(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


LATENT_TOPOLOGY = {
    "kind": "distance_labeled_ring",
    "nodes": NODES,
    "distances": "cyclic",
    "available_offsets": list(range(1, (NODES // 2) + 1)),
}
UPDATE_RULE = {
    "kind": "fixed_mean_message_passing",
    "rounds": ROUNDS,
    "fanout": FANOUT,
    "neighbors": ["-2s", "-s", "+s", "+2s"],
    "self_weight": 1,
    "peer_weight": 1,
    "normalizer": 5,
}
TASKSET = {
    "families": ["segmented", "transfer", "counterfactual"],
    "episodes_per_family": EPISODES_PER_FAMILY,
    "segmented_block": SEGMENT_BLOCK,
    "transfer_block": TRANSFER_BLOCK,
    "noise_p": NOISE_P,
}
COMPUTE_BUDGET = {
    "rounds": ROUNDS,
    "messages_per_node_per_round": FANOUT,
    "scalar_state_channels": 1,
}

INVARIANTS = {
    "node_set": digest({"nodes": list(range(NODES))}),
    "topology": digest(LATENT_TOPOLOGY),
    "initial_state": digest({"encoding": "one signed scalar per node", "range": [-1, 1]}),
    "taskset": digest(TASKSET),
    "compute_budget": digest(COMPUTE_BUDGET),
    "update_rule": digest(UPDATE_RULE),
}


def sign(x: float) -> int:
    return 1 if x >= 0 else -1


def evolve(values: list[float], scale: int) -> list[float]:
    state = list(values)
    offsets = (-2 * scale, -scale, scale, 2 * scale)
    for _ in range(ROUNDS):
        state = [
            (state[i] + sum(state[(i + offset) % NODES] for offset in offsets)) / 5.0
            for i in range(NODES)
        ]
    return state


def noisy_blocks(rng: random.Random, block: int, rotation: int = 0) -> list[float]:
    values = [0.0] * NODES
    block_count = (NODES + block - 1) // block
    block_signs = [rng.choice((-1, 1)) for _ in range(block_count)]
    for i in range(NODES):
        source = (i - rotation) % NODES
        base = block_signs[(source // block) % block_count]
        if rng.random() < NOISE_P:
            base *= -1
        values[i] = float(base)
    return values


def force_nonzero_majority(values: list[float], rng: random.Random) -> list[float]:
    total = int(sum(values))
    if total != 0:
        return values
    idx = rng.randrange(NODES)
    values = list(values)
    values[idx] = 1.0
    return values


def majority_accuracy(final: list[float], initial: list[float]) -> float:
    target = sign(sum(initial))
    return sum(sign(value) == target for value in final) / NODES


def mean_estimation_score(final: list[float], initial: list[float]) -> float:
    target = mean(initial)
    mae = mean(abs(value - target) for value in final)
    return max(0.0, min(1.0, 1.0 - mae))


def counterfactual_pair(rng: random.Random) -> tuple[list[float], list[float]]:
    # Exactly 32 of one sign and 31 of the other, then flip one majority bit.
    majority = rng.choice((-1, 1))
    values = [float(majority)] * 32 + [float(-majority)] * 31
    rng.shuffle(values)
    pivot = next(i for i, value in enumerate(values) if value == majority)
    changed = list(values)
    changed[pivot] = float(-majority)
    return values, changed


def run_replicate(scale: int, seed: int) -> dict[str, float]:
    rng = random.Random(seed)

    segmented_acc = []
    transfer_acc = []
    integration_scores = []
    counterfactual_scores = []

    for _ in range(EPISODES_PER_FAMILY):
        initial = force_nonzero_majority(noisy_blocks(rng, SEGMENT_BLOCK), rng)
        final = evolve(initial, scale)
        segmented_acc.append(majority_accuracy(final, initial))
        integration_scores.append(mean_estimation_score(final, initial))

    for _ in range(EPISODES_PER_FAMILY):
        rotation = rng.randrange(TRANSFER_BLOCK)
        initial = force_nonzero_majority(
            noisy_blocks(rng, TRANSFER_BLOCK, rotation=rotation), rng
        )
        final = evolve(initial, scale)
        transfer_acc.append(majority_accuracy(final, initial))

    for _ in range(EPISODES_PER_FAMILY):
        before, after = counterfactual_pair(rng)
        before_final = evolve(before, scale)
        after_final = evolve(after, scale)
        before_target = sign(sum(before))
        after_target = sign(sum(after))
        tracked = sum(
            sign(a) == before_target and sign(b) == after_target
            for a, b in zip(before_final, after_final)
        ) / NODES
        counterfactual_scores.append(tracked)

    return {
        "task_success": mean(segmented_acc),
        "cross_context_transfer": mean(transfer_acc),
        "distributed_integration": mean(integration_scores),
        "counterfactual_adaptation": mean(counterfactual_scores),
    }


def run_sweep() -> dict[str, object]:
    trials = []
    for scale in SCALES:
        for replicate, seed in enumerate(REPLICATE_SEEDS):
            trials.append(
                {
                    "interaction_scale": scale,
                    "replicate": replicate,
                    "seed": seed,
                    "invariants": dict(INVARIANTS),
                    "phenotype": run_replicate(scale, seed),
                }
            )

    verdict = evaluate(trials)
    return {
        "protocol": "SCALE-INTELLIGENCE-01",
        "configuration": {
            "nodes": NODES,
            "scales": list(SCALES),
            "replicate_seeds": list(REPLICATE_SEEDS),
            "rounds": ROUNDS,
            "fanout": FANOUT,
            "episodes_per_family": EPISODES_PER_FAMILY,
            "segmented_block": SEGMENT_BLOCK,
            "transfer_block": TRANSFER_BLOCK,
            "noise_p": NOISE_P,
        },
        "invariants": INVARIANTS,
        "trials": trials,
        "verdict": verdict,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_sweep_result.json")
    args = parser.parse_args()
    result = run_sweep()
    path = Path(args.output)
    path.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
