#!/usr/bin/env python3
"""Run SCALE-EFFICIENCY-08 on the frozen ring substrate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scale_compression_run import probe_replicate
from scale_efficiency_falsifier import evaluate
from scale_sweep import EPISODES_PER_FAMILY, INVARIANTS, SCALES, run_replicate

REPLICATE_SEEDS = (22022, 23023, 24024, 25025, 26026)


def run_experiment() -> dict[str, object]:
    trials = []
    for scale in SCALES:
        for replicate, seed in enumerate(REPLICATE_SEEDS):
            compression = probe_replicate(scale, seed)
            base = run_replicate(scale, seed)
            trials.append(
                {
                    "interaction_scale": scale,
                    "replicate": replicate,
                    "seed": seed,
                    "invariants": dict(INVARIANTS),
                    "target_decodability": float(compression["target_decodability"]),
                    "nuisance_compression": float(compression["nuisance_compression"]),
                    "information_efficiency": float(compression["sufficient_compression"]),
                    "capability": 0.5 * (
                        float(base["task_success"]) + float(base["cross_context_transfer"])
                    ),
                }
            )

    return {
        "protocol": "SCALE-EFFICIENCY-08",
        "canonical_base": "1d8271cbe4d0e63d4edf5221cc5ce3c677fc0834",
        "preregistration_sha": "16e4a2fe357ddd26589c693e19ebc3a628106fbb",
        "replicate_seeds": list(REPLICATE_SEEDS),
        "scales": list(SCALES),
        "episodes_per_scale_replicate": EPISODES_PER_FAMILY,
        "continuous_model": "OLS quadratic in log2(interaction_scale) over five aggregate scale means",
        "information_efficiency": "harmonic mean(target_decodability, nuisance_compression), unchanged from SCALE-COMPRESSION-07",
        "capability": "mean(task_success, cross_context_transfer), independently measured",
        "invariants": dict(INVARIANTS),
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_efficiency_08_result.json")
    args = parser.parse_args()
    result = run_experiment()
    Path(args.output).write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
