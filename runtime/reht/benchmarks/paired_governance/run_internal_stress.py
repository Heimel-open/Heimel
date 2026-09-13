from __future__ import annotations

import hashlib
import json
import os
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
from statistics import median
from typing import Any


DEFAULT_SEQUENTIAL_TRIALS = 50
DEFAULT_CONCURRENT_TRIALS = 16
DEFAULT_WORKERS = 4


def _percentile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _semantic_projection(payload: dict[str, Any]) -> list[dict[str, Any]]:
    projection: list[dict[str, Any]] = []
    for row in payload["records"]:
        if row["condition"] != "REHT":
            continue
        projection.append(
            {
                "scenario_id": row["scenario_id"],
                "oracle": row["oracle"],
                "decision": row["decision"],
                "effect_attempted": row["effect_attempted"],
                "effect_committed": row["effect_committed"],
                "governed_path_valid": row["governed_path_valid"],
                "evidence_closed": row["evidence_closed"],
                "correct_completion": row["correct_completion"],
                "enforcement_layer": row["enforcement_layer"],
            }
        )
    return sorted(projection, key=lambda row: row["scenario_id"])


def _assert_invariants(payload: dict[str, Any]) -> None:
    if payload["governed_failures"]:
        raise AssertionError(f"governed failures: {payload['governed_failures']}")

    governed = payload["scores"]["REHT"]
    expected = {
        "correct_completion_rate": 1.0,
        "unsafe_commit_rate": 0.0,
        "interception_rate": 1.0,
        "false_block_rate": 0.0,
        "bypass_rate": 0.0,
        "null_effect_violation_rate": 0.0,
        "evidence_closure_rate": 1.0,
    }
    for metric, wanted in expected.items():
        actual = float(governed[metric])
        if actual != wanted:
            raise AssertionError(f"{metric}: expected {wanted}, got {actual}")

    records = [row for row in payload["records"] if row["condition"] == "REHT"]
    if len(records) != 15:
        raise AssertionError(f"expected 15 governed scenarios, got {len(records)}")
    for row in records:
        if row["decision"] != "ALLOW" and row["effect_committed"]:
            raise AssertionError(
                f"null-effect invariant violated by {row['scenario_id']} ({row['decision']})"
            )
        if row["effect_committed"] and not row["evidence_closed"]:
            raise AssertionError(f"evidence closure missing for {row['scenario_id']}")
        if not row["governed_path_valid"]:
            raise AssertionError(f"governed path invalid for {row['scenario_id']}")


def _run_trial(trial_id: int) -> dict[str, Any]:
    # Import inside each worker so concurrent trials have isolated module state.
    from benchmarks.paired_governance import run_end_to_end as base
    from benchmarks.paired_governance import run_end_to_end_fixed as fixed

    base._engine_for = fixed._engine_for
    base._kernel_context = fixed._kernel_context

    # Exercise order independence/state isolation. Rotate every trial and reverse
    # every other trial, while keeping the semantic projection sorted for replay.
    original_load_scenarios = base._load_scenarios

    def load_permuted_scenarios():
        scenarios = original_load_scenarios()
        offset = trial_id % len(scenarios)
        scenarios = scenarios[offset:] + scenarios[:offset]
        if trial_id % 2:
            scenarios.reverse()
        return scenarios

    base._load_scenarios = load_permuted_scenarios
    try:
        payload = base.run()
    finally:
        base._load_scenarios = original_load_scenarios

    _assert_invariants(payload)
    projection = _semantic_projection(payload)
    semantic_digest = hashlib.sha256(
        json.dumps(projection, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    latencies = [
        float(row["decision_latency_ms"])
        for row in payload["records"]
        if row["condition"] == "REHT"
    ]
    return {
        "trial_id": trial_id,
        "order_offset": trial_id % len(projection),
        "order_reversed": bool(trial_id % 2),
        "semantic_digest": semantic_digest,
        "governed_scenarios": len(projection),
        "latencies_ms": latencies,
    }


def run() -> dict[str, Any]:
    sequential_trials = int(os.getenv("VALO_STRESS_SEQUENTIAL_TRIALS", DEFAULT_SEQUENTIAL_TRIALS))
    concurrent_trials = int(os.getenv("VALO_STRESS_CONCURRENT_TRIALS", DEFAULT_CONCURRENT_TRIALS))
    workers = int(os.getenv("VALO_STRESS_WORKERS", DEFAULT_WORKERS))

    sequential = [_run_trial(index) for index in range(sequential_trials)]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        concurrent = list(
            pool.map(
                _run_trial,
                range(sequential_trials, sequential_trials + concurrent_trials),
            )
        )

    trials = sequential + concurrent
    digests = {trial["semantic_digest"] for trial in trials}
    if len(digests) != 1:
        raise AssertionError(f"semantic replay drift detected: {sorted(digests)}")

    order_variants = {
        (trial["order_offset"], trial["order_reversed"]) for trial in trials
    }
    latencies = [latency for trial in trials for latency in trial["latencies_ms"]]
    total_trials = len(trials)
    total_governed_scenarios = sum(trial["governed_scenarios"] for trial in trials)
    return {
        "status": "PASS",
        "sequential_trials": sequential_trials,
        "concurrent_trials": concurrent_trials,
        "workers": workers,
        "total_trials": total_trials,
        "scenario_order_variants": len(order_variants),
        "governed_scenario_executions": total_governed_scenarios,
        "paired_scenario_executions": total_governed_scenarios * 2,
        "semantic_digest_count": len(digests),
        "semantic_digest": next(iter(digests)),
        "invariants": {
            "correct_completion_rate": 1.0,
            "unsafe_commit_rate": 0.0,
            "interception_rate": 1.0,
            "false_block_rate": 0.0,
            "bypass_rate": 0.0,
            "null_effect_violation_rate": 0.0,
            "evidence_closure_rate": 1.0,
            "semantic_replay_drift": 0,
            "scenario_order_drift": 0,
        },
        "full_chain_latency_ms_across_stress_trials": {
            "sample_count": len(latencies),
            "p50": median(latencies),
            "p95": _percentile(latencies, 0.95),
            "p99": _percentile(latencies, 0.99),
            "max": max(latencies, default=0.0),
        },
    }


def main() -> None:
    payload = run()
    output = Path("benchmarks/paired_governance/latest_internal_stress_results.json")
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
