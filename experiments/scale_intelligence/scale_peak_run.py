#!/usr/bin/env python3
"""Run SCALE-PEAK-10 dense nonparametric peak localization."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scale_geometry_run import (
    NON_GEOMETRY_INVARIANTS,
    capability_probe,
    efficiency_probe,
)
from scale_peak_falsifier import evaluate
from scale_sweep import EPISODES_PER_FAMILY

TASK_BLOCKS = (5, 9, 13)
DENSE_SCALES = tuple(range(4, 16))
REPLICATE_SEEDS = (32032, 33033, 34034, 35035, 36036)


def run_experiment() -> dict[str, object]:
    trials = []
    for block in TASK_BLOCKS:
        for scale in DENSE_SCALES:
            for replicate, seed in enumerate(REPLICATE_SEEDS):
                efficiency = efficiency_probe(scale, seed, block)
                trials.append(
                    {
                        "task_block": block,
                        "interaction_scale": scale,
                        "replicate": replicate,
                        "seed": seed,
                        "non_geometry_invariants": dict(NON_GEOMETRY_INVARIANTS),
                        "target_decodability": float(efficiency["target_decodability"]),
                        "nuisance_compression": float(efficiency["nuisance_compression"]),
                        "information_efficiency": float(efficiency["information_efficiency"]),
                        "capability": float(capability_probe(scale, seed, block)),
                    }
                )

    return {
        "protocol": "SCALE-PEAK-10",
        "canonical_base": "52758c999ca8d9d4bb1874d1a4db37165a75223c",
        "preregistration_sha": "ec0ec6364dbe69bce910e846caaf926a9f96e64e",
        "task_blocks": list(TASK_BLOCKS),
        "scales": list(DENSE_SCALES),
        "replicate_seeds": list(REPLICATE_SEEDS),
        "episodes_per_probe_stream": EPISODES_PER_FAMILY,
        "peak_rule": "exact observed argmax per replicate; arithmetic mean of exact tied maxima; median of five replicate peaks",
        "non_geometry_invariants": dict(NON_GEOMETRY_INVARIANTS),
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_peak_10_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
