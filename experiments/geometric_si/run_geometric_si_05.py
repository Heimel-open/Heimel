#!/usr/bin/env python3
"""LOCAL EXECUTION REQUIRED: GEOMETRIC-SI-05."""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path

from geometric_si_05 import run_experiment


def git_head() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    except Exception:
        return "UNKNOWN"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=64)
    parser.add_argument("--out", type=Path, default=Path("experiments/geometric_si/results/GEOMETRIC-SI-05.json"))
    args = parser.parse_args()
    if args.seeds < 2:
        raise SystemExit("--seeds must be >= 2")
    started = time.time()
    runs = run_experiment(range(args.seeds))
    metrics = [run["metrics"] for run in runs]
    mean = lambda key: sum(item[key] for item in metrics) / len(metrics)
    summary = {key: mean(key) for key in metrics[0]}
    gates = {
        "checkpoint_explicit_information_equal": all(run["checkpoint"]["explicit_facts_equal"] and run["checkpoint"]["capabilities_equal"] for run in runs),
        "path_divergence_present": summary["trajectory_divergence"] > 0.0,
        "history_reset_removes_divergence": summary["reset_divergence"] == 0.0,
        "history_rewire_changes_trajectory": summary["rewire_choice_difference"] > 0.0,
        "same_history_replays": summary["replay_choice_match"] == 1.0,
    }
    bundle = {
        "experiment": "GEOMETRIC-SI-05",
        "title": "Developmental Path Dependence",
        "execution_requirement": "LOCAL EXECUTION REQUIRED",
        "git_head": git_head(),
        "parameters": {"seeds": list(range(args.seeds)), "probe": 6, "nursery_paths": ["A", "B"]},
        "runtime": {"python": sys.version, "platform": platform.platform(), "machine": platform.machine()},
        "elapsed_seconds": time.time() - started,
        "hypotheses": {"H1": "History affects later development after explicit checkpoint information is controlled.", "H0": "Controlling checkpoint information removes systematic differences."},
        "summary": summary,
        "gates": gates,
        "classification": "H1_SUPPORTED_BOUNDED_PATH_DEPENDENCE" if all(gates.values()) else "H1_NOT_SUPPORTED_BY_THIS_HARNESS",
        "runs": runs,
        "interpretation_constraints": [
            "Evidence is bounded to this deterministic developmental harness.",
            "Checkpoint equality covers explicit facts and declared task capability; latent organization is intentionally not normalized.",
            "A positive result does not establish consciousness, identity, or substrate independence.",
        ],
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    print(args.out)
    print(bundle["classification"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
