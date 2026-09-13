#!/usr/bin/env python3
"""LOCAL EXECUTION REQUIRED.

Runs GEOMETRIC-SI-02 locally. GitHub stores source and evidence only.
No benchmark result may be inferred from this file or from CI status.
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from pathlib import Path
from statistics import mean

from paios.geometric_si import Ablation, AgentState, GeometricState, Relation, SymbolicState, nursery_state

TASKS = (
    ("association", lambda state: state.strongest_target("signal-a", "means") == "safe"),
    ("composition", lambda state: "delta" in state.reachable("alpha", "path")),
    ("choice_consistency", lambda state: state.strongest_target("self", "prefers") == "explore"),
    ("partner_recognition", lambda state: state.strongest_target("partner-pattern", "partner") == "p7"),
)


def git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return "UNKNOWN"


def canonical_geo(state: GeometricState) -> bytes:
    rows = [
        {
            "source": r.source,
            "kind": r.kind,
            "target": r.target,
            "weight": r.weight,
            "provenance": r.provenance,
        }
        for r in sorted(state.edges.values(), key=lambda r: (r.source, r.kind, r.target))
    ]
    return json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()


def canonical_symbolic(state: SymbolicState) -> bytes:
    rows = [
        {
            "source": r.source,
            "kind": r.kind,
            "target": r.target,
            "weight": r.weight,
            "provenance": r.provenance,
        }
        for r in state.records
    ]
    return json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()


def load_geo(payload: bytes) -> GeometricState:
    out = GeometricState()
    for row in json.loads(payload):
        out.learn(Relation(**row))
    return out


def load_symbolic(payload: bytes) -> SymbolicState:
    out = SymbolicState()
    for row in json.loads(payload):
        out.learn(Relation(**row))
    return out


def logical_ops_geo(state: GeometricState) -> int:
    # Count relation inspections implied by the current implementation for the
    # preregistered four queries. This intentionally measures the implementation
    # as it exists rather than granting an optimized index after outcome.
    n = len(state.edges)
    # strongest_target scans all edges for three tasks.
    strongest = 3 * n
    # reachable(alpha,path): current neighbors() scans all edges once per visited
    # path node. Nursery path visits alpha, beta, gamma, delta => four scans.
    composition = 4 * n
    return strongest + composition


def logical_ops_symbolic(state: SymbolicState) -> int:
    n = len(state.records)
    # strongest_target scans all records for three tasks.
    strongest = 3 * n
    # reachable() builds adjacency by scanning records once, then traverses the
    # built adjacency. Count the relation scan plus four node adjacency lookups.
    composition = n + 4
    return strongest + composition


def score(state: AgentState) -> dict[str, float]:
    result = {name: float(fn(state)) for name, fn in TASKS}
    result["acquired_score"] = mean(result.values())
    return result


def timed_queries(state: AgentState, repetitions: int) -> float:
    started = time.perf_counter_ns()
    for _ in range(repetitions):
        for _, fn in TASKS:
            fn(state)
    return (time.perf_counter_ns() - started) / repetitions


def timed_load(payload: bytes, loader, repetitions: int) -> float:
    started = time.perf_counter_ns()
    for _ in range(repetitions):
        loader(payload)
    return (time.perf_counter_ns() - started) / repetitions


def one_seed(seed: int, repetitions: int, load_repetitions: int) -> dict:
    base = nursery_state()
    geo_agent = base.ablate(Ablation.GEO, seed)
    symbolic_agent = base.ablate(Ablation.SYMBOLIC, seed)

    geo_payload = canonical_geo(geo_agent.geometry)
    sym_payload = canonical_symbolic(symbolic_agent.symbolic)

    geo_score = score(geo_agent)
    sym_score = score(symbolic_agent)

    return {
        "seed": seed,
        "geo": {
            "score": geo_score,
            "serialized_state_bytes": len(geo_payload),
            "relation_count": len(geo_agent.geometry.edges),
            "logical_query_operations": logical_ops_geo(geo_agent.geometry),
            "query_ns_per_four_task_bundle": timed_queries(geo_agent, repetitions),
            "load_ns": timed_load(geo_payload, load_geo, load_repetitions),
        },
        "symbolic": {
            "score": sym_score,
            "serialized_state_bytes": len(sym_payload),
            "record_count": len(symbolic_agent.symbolic.records),
            "logical_query_operations": logical_ops_symbolic(symbolic_agent.symbolic),
            "query_ns_per_four_task_bundle": timed_queries(symbolic_agent, repetitions),
            "load_ns": timed_load(sym_payload, load_symbolic, load_repetitions),
        },
    }


def summarize(runs: list[dict], tolerance: float) -> dict:
    geo_scores = [r["geo"]["score"]["acquired_score"] for r in runs]
    sym_scores = [r["symbolic"]["score"]["acquired_score"] for r in runs]
    perf_delta = abs(mean(geo_scores) - mean(sym_scores))
    equivalent = perf_delta <= tolerance

    def avg(side: str, key: str) -> float:
        return mean(r[side][key] for r in runs)

    return {
        "performance": {
            "geo_mean": mean(geo_scores),
            "symbolic_mean": mean(sym_scores),
            "absolute_delta": perf_delta,
            "tolerance": tolerance,
            "equivalent": equivalent,
        },
        "cost_means": {
            "geo": {
                "serialized_state_bytes": avg("geo", "serialized_state_bytes"),
                "logical_query_operations": avg("geo", "logical_query_operations"),
                "query_ns_per_four_task_bundle": avg("geo", "query_ns_per_four_task_bundle"),
                "load_ns": avg("geo", "load_ns"),
            },
            "symbolic": {
                "serialized_state_bytes": avg("symbolic", "serialized_state_bytes"),
                "logical_query_operations": avg("symbolic", "logical_query_operations"),
                "query_ns_per_four_task_bundle": avg("symbolic", "query_ns_per_four_task_bundle"),
                "load_ns": avg("symbolic", "load_ns"),
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=20)
    parser.add_argument("--repetitions", type=int, default=10000)
    parser.add_argument("--load-repetitions", type=int, default=1000)
    parser.add_argument("--performance-tolerance", type=float, default=0.0)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("experiments/geometric_si/results/GEOMETRIC-SI-02.json"),
    )
    args = parser.parse_args()

    if args.seeds < 1 or args.repetitions < 1 or args.load_repetitions < 1:
        raise SystemExit("seeds/repetitions/load-repetitions must be >= 1")
    if args.performance_tolerance < 0:
        raise SystemExit("performance tolerance must be >= 0")

    started = time.time()
    runs = [one_seed(seed, args.repetitions, args.load_repetitions) for seed in range(args.seeds)]
    summary = summarize(runs, args.performance_tolerance)

    bundle = {
        "experiment": "GEOMETRIC-SI-02",
        "execution_requirement": "LOCAL EXECUTION REQUIRED",
        "git_head": git_head(),
        "parameters": {
            "seeds": list(range(args.seeds)),
            "query_repetitions_per_seed": args.repetitions,
            "load_repetitions_per_seed": args.load_repetitions,
            "performance_tolerance": args.performance_tolerance,
        },
        "runtime": {
            "python": sys.version,
            "platform": platform.platform(),
            "machine": platform.machine(),
            "processor": platform.processor(),
        },
        "elapsed_seconds": time.time() - started,
        "summary": summary,
        "runs": runs,
        "interpretation_constraints": [
            "Cost comparison is admissible only if performance equivalence is true.",
            "Wall-clock timing is local-runtime evidence and must not be generalized across hardware without replication.",
            "Logical operation counts describe the current implementation, not an information-theoretic lower bound.",
            "A cost advantage does not establish that SI is fundamentally geometric.",
        ],
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(bundle, indent=2, sort_keys=True) + "\n")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
