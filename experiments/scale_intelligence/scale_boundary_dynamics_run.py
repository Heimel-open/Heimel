#!/usr/bin/env python3
"""Run SCALE-BOUNDARY-DYNAMICS-13."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from statistics import mean

from scale_boundary_dynamics_falsifier import evaluate
from scale_boundary_run import INTERIOR, region_accuracy, region_distance
from scale_compression_run import harmonic, nuisance_twin
from scale_sweep import (
    EPISODES_PER_FAMILY,
    INVARIANTS,
    NODES,
    ROUNDS,
    digest,
    force_nonzero_majority,
    noisy_blocks,
)
from scale_topology_run import (
    DENSE_SCALES,
    TASK_BLOCKS,
    TOPOLOGY_SPEC,
    evolve_reflected,
)

REPLICATE_SEEDS = (47047, 48048, 49049, 50050, 51051)

SELF_PADDED_SPEC = {
    "kind": "self_padded_line",
    "nodes": NODES,
    "endpoints": [0, NODES - 1],
    "offsets": ["-2s", "-s", "+s", "+2s"],
    "boundary_rule": "if peer address is out of bounds, resolve that message slot to receiver i",
}
COMMON_INVARIANTS = {
    "node_set": INVARIANTS["node_set"],
    "initial_state": INVARIANTS["initial_state"],
    "compute_budget": INVARIANTS["compute_budget"],
    "update_rule": INVARIANTS["update_rule"],
}
CONDITION_INVARIANTS = {
    "reflected": {
        **COMMON_INVARIANTS,
        "topology": digest(TOPOLOGY_SPEC),
    },
    "self_padded": {
        **COMMON_INVARIANTS,
        "topology": digest(SELF_PADDED_SPEC),
    },
}


def evolve_self_padded(values: list[float], scale: int) -> list[float]:
    state = list(values)
    offsets = (-2 * scale, -scale, scale, 2 * scale)
    for _ in range(ROUNDS):
        next_state = []
        for i in range(NODES):
            messages = []
            for offset in offsets:
                peer = i + offset
                messages.append(state[peer] if 0 <= peer < NODES else state[i])
            next_state.append((state[i] + sum(messages)) / 5.0)
        state = next_state
    return state


EVOLVERS = {
    "reflected": evolve_reflected,
    "self_padded": evolve_self_padded,
}


def efficiency_probe_pair(
    scale: int, seed: int, block: int
) -> dict[str, dict[str, float]]:
    rng = random.Random(seed + block * 100000)
    dec = {condition: [] for condition in EVOLVERS}
    comp = {condition: [] for condition in EVOLVERS}

    for _ in range(EPISODES_PER_FAMILY):
        initial = force_nonzero_majority(noisy_blocks(rng, block), rng)
        twin = nuisance_twin(initial, rng)
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
            if initial_distance <= 0.0:
                comp[condition].append(0.0)
            else:
                comp[condition].append(
                    max(
                        0.0,
                        min(
                            1.0,
                            1.0 - final_distance / initial_distance,
                        ),
                    )
                )

    out = {}
    for condition in EVOLVERS:
        td = mean(dec[condition])
        nc = mean(comp[condition])
        out[condition] = {
            "target_decodability": td,
            "nuisance_compression": nc,
            "information_efficiency": harmonic(td, nc),
        }
    return out


def capability_probe_pair(
    scale: int, seed: int, block: int
) -> dict[str, float]:
    unrotated_rng = random.Random(seed + block * 100000 + 1000000)
    rotated_rng = random.Random(seed + block * 100000 + 2000000)
    scores = {condition: [] for condition in EVOLVERS}

    for _ in range(EPISODES_PER_FAMILY):
        initial = force_nonzero_majority(
            noisy_blocks(unrotated_rng, block), unrotated_rng
        )
        for condition, evolve in EVOLVERS.items():
            scores[condition].append(
                region_accuracy(evolve(initial, scale), initial, INTERIOR)
            )

    for _ in range(EPISODES_PER_FAMILY):
        rotation = rotated_rng.randrange(block)
        initial = force_nonzero_majority(
            noisy_blocks(rotated_rng, block, rotation=rotation), rotated_rng
        )
        for condition, evolve in EVOLVERS.items():
            scores[condition].append(
                region_accuracy(evolve(initial, scale), initial, INTERIOR)
            )

    return {
        condition: mean(values)
        for condition, values in scores.items()
    }


def run_experiment() -> dict[str, object]:
    trials = []
    for block in TASK_BLOCKS:
        for scale in DENSE_SCALES:
            for replicate, seed in enumerate(REPLICATE_SEEDS):
                efficiency = efficiency_probe_pair(scale, seed, block)
                capability = capability_probe_pair(scale, seed, block)
                for condition in EVOLVERS:
                    trials.append(
                        {
                            "boundary_condition": condition,
                            "task_block": block,
                            "interaction_scale": scale,
                            "replicate": replicate,
                            "seed": seed,
                            "condition_invariants": dict(
                                CONDITION_INVARIANTS[condition]
                            ),
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
                        }
                    )

    return {
        "protocol": "SCALE-BOUNDARY-DYNAMICS-13",
        "canonical_base": "99a75b22f3de4239fef380ca2e82bc441f504654",
        "preregistration_sha": "3253fdaca235ba049ecdbead31b99a0b55c69b24",
        "task_blocks": list(TASK_BLOCKS),
        "scales": list(DENSE_SCALES),
        "replicate_seeds": list(REPLICATE_SEEDS),
        "episodes_per_probe_stream": EPISODES_PER_FAMILY,
        "scoring_region": [INTERIOR[0], INTERIOR[-1], len(INTERIOR)],
        "boundary_conditions": {
            "reflected": TOPOLOGY_SPEC,
            "self_padded": SELF_PADDED_SPEC,
        },
        "condition_invariants": CONDITION_INVARIANTS,
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output", default="scale_boundary_dynamics_13_result.json"
    )
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
