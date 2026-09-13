#!/usr/bin/env python3
"""Run the frozen SCALE-SEPARATION-02 replication on fresh seeds."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scale_separation_falsifier import evaluate
from scale_sweep import INVARIANTS, SCALES, run_replicate

REPLICATE_SEEDS = (404, 505, 606)


def run_replication() -> dict[str, object]:
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

    return {
        "protocol": "SCALE-SEPARATION-02",
        "replication_of": "SCALE-INTELLIGENCE-01 diagnostic separation",
        "replicate_seeds": list(REPLICATE_SEEDS),
        "scales": list(SCALES),
        "invariants": dict(INVARIANTS),
        "trials": trials,
        "verdict": evaluate(trials),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="scale_separation_02_result.json")
    args = parser.parse_args()
    result = run_replication()
    Path(args.output).write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(result["verdict"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
