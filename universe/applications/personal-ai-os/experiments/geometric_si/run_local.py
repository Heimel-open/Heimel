#!/usr/bin/env python3
"""LOCAL EXECUTION REQUIRED.

Runs GEOMETRIC-SI-01 locally and emits a provenance-bearing JSON evidence bundle.
This script is intentionally not wired into GitHub Actions.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from statistics import mean

from paios.geometric_si import Ablation, run_experiment


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "UNKNOWN"


def summarize(results):
    summary = {}
    for mode, runs in results.items():
        summary[mode.value] = {
            "n": len(runs),
            "association_mean": mean(r.association for r in runs),
            "composition_mean": mean(r.composition for r in runs),
            "choice_consistency_mean": mean(r.choice_consistency for r in runs),
            "partner_recognition_mean": mean(r.partner_recognition for r in runs),
            "acquired_score_mean": mean(r.acquired_score for r in runs),
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("experiments/geometric_si/results/GEOMETRIC-SI-01.json"),
    )
    args = parser.parse_args()

    if args.seeds < 1:
        raise SystemExit("--seeds must be >= 1")

    started = time.time()
    seed_set = list(range(args.seeds))
    results = run_experiment(seed_set)
    elapsed = time.time() - started

    bundle = {
        "experiment": "GEOMETRIC-SI-01",
        "execution_requirement": "LOCAL EXECUTION REQUIRED",
        "git_head": git_head(),
        "parameters": {"seeds": seed_set},
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "elapsed_seconds": elapsed,
        "summary": summarize(results),
        "runs": {
            mode.value: [asdict(run) | {"mode": run.mode.value} for run in runs]
            for mode, runs in results.items()
        },
        "interpretation_constraints": [
            "GEO > RESET is evidence only for this harness and representation.",
            "GEO == SYMBOLIC does not establish geometric superiority.",
            "No result establishes consciousness, identity, or substrate independence.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
