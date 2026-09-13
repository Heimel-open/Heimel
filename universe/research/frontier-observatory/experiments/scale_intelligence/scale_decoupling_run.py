#!/usr/bin/env python3
"""Run SCALE-DECOUPLING-14 using the frozen boundary intervention."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scale_boundary_dynamics_run import (
    CONDITION_INVARIANTS,
    EVOLVERS,
    capability_probe_pair,
    efficiency_probe_pair,
)
from scale_decoupling_falsifier import evaluate
from scale_sweep import EPISODES_PER_FAMILY
from scale_topology_run import DENSE_SCALES, TASK_BLOCKS

REPLICATE_SEEDS = (52052, 53053, 54054, 55055, 56056)


def run_experiment():
    trials = []
    for block in TASK_BLOCKS:
        for scale in DENSE_SCALES:
            for replicate, seed in enumerate(REPLICATE_SEEDS):
                efficiency = efficiency_probe_pair(scale, seed, block)
                capability = capability_probe_pair(scale, seed, block)
                for condition in EVOLVERS:
                    trials.append({
                        "boundary_condition": condition,
                        "task_block": block,
                        "interaction_scale": scale,
                        "replicate": replicate,
                        "seed": seed,
                        "condition_invariants": dict(CONDITION_INVARIANTS[condition]),
                        "target_decodability": float(efficiency[condition]["target_decodability"]),
                        "nuisance_compression": float(efficiency[condition]["nuisance_compression"]),
                        "information_efficiency": float(efficiency[condition]["information_efficiency"]),
                        "capability": float(capability[condition]),
                    })
    return {
        "protocol": "SCALE-DECOUPLING-14",
        "canonical_base": "cab3c0e89a24fb254ccf575720d0b1c85fd23cb9",
        "preregistration_sha": "821458c277d5be260e013f91da6c21a90929fe8f",
        "task_blocks": list(TASK_BLOCKS),
        "scales": list(DENSE_SCALES),
        "replicate_seeds": list(REPLICATE_SEEDS),
        "episodes_per_probe_stream": EPISODES_PER_FAMILY,
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_decoupling_14_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
