#!/usr/bin/env python3
"""Run SCALE-RATIO-15 on held-out task geometries."""

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
from scale_ratio_falsifier import BLOCKS, SCALES, evaluate
from scale_sweep import EPISODES_PER_FAMILY

REPLICATE_SEEDS = (57057, 58058, 59059, 60060, 61061)


def run_experiment() -> dict[str, object]:
    trials = []
    for block in BLOCKS:
        for scale in SCALES:
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
                            "condition_invariants": dict(CONDITION_INVARIANTS[condition]),
                            "target_decodability": float(efficiency[condition]["target_decodability"]),
                            "nuisance_compression": float(efficiency[condition]["nuisance_compression"]),
                            "information_efficiency": float(efficiency[condition]["information_efficiency"]),
                            "capability": float(capability[condition]),
                        }
                    )
    return {
        "protocol": "SCALE-RATIO-15",
        "canonical_base": "01e598bbd5c42dcf710cc10eeb2ee5ca23449677",
        "preregistration_sha": "27424f2fd742e621b3ba1acdd656e0a99a2914fd",
        "task_blocks": list(BLOCKS),
        "scales": list(SCALES),
        "replicate_seeds": list(REPLICATE_SEEDS),
        "episodes_per_probe_stream": EPISODES_PER_FAMILY,
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_ratio_15_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
