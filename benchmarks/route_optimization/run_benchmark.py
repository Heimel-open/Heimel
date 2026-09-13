#!/usr/bin/env python3
"""Run representative action-frontier structural and timing benchmarks."""

from __future__ import annotations

import argparse
import itertools
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter_ns
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.valo_platform.route_optimization import (  # noqa: E402
    ConstraintKind,
    RecoveryMode,
    RecoveryRouteOption,
    RouteCandidate,
    RouteConstraint,
    RouteEdge,
    RouteEstimate,
    RouteGraph,
    RouteNode,
    RouteNodeKind,
    RouteReasonCode,
    RouteRequest,
    reduce_frontier,
    select_fastest_valid_route,
    select_recovery_route,
)


NOW = datetime(2026, 7, 27, 8, 0, tzinfo=timezone.utc)


def route_request(identifier: str) -> RouteRequest:
    return RouteRequest(
        route_request_id=identifier,
        principal_id="principal-1",
        purpose_ref="benchmark-purpose",
        intent_digest="sha256:intent",
        semantic_state_digest="sha256:semantic",
        target_outcome_ref="benchmark-outcome",
        current_state_digest="sha256:state",
        authority_snapshot_hash="sha256:authority",
        policy_snapshot_hash="sha256:policy",
        context_snapshot_hash="sha256:context",
        as_of=NOW,
        estimate_set_version="benchmark-v1",
    )


def benchmark_sparse_frontier() -> tuple[dict[str, Any], tuple[Any, ...]]:
    target = RouteNode(
        node_id="target",
        kind=RouteNodeKind.OUTCOME,
        estimate=RouteEstimate(evidence_strength=100, version="benchmark-v1"),
    )
    best = RouteNode(
        node_id="best",
        kind=RouteNodeKind.MODEL,
        estimate=RouteEstimate(
            execution_ms=10,
            cost_microunits=10,
            evidence_strength=100,
            version="benchmark-v1",
        ),
    )
    dominated_nodes = tuple(
        RouteNode(
            node_id=f"dominated-{index:02d}",
            kind=RouteNodeKind.MODEL,
            estimate=RouteEstimate(
                execution_ms=20 + index,
                cost_microunits=20 + index,
                risk_exposure=1,
                evidence_strength=100,
                version="benchmark-v1",
            ),
        )
        for index in range(32)
    )
    graph = RouteGraph(
        graph_id="sparse-frontier",
        graph_version="1",
        target_node_id="target",
        nodes=(target, best, *dominated_nodes),
        edges=(
            RouteEdge(source="best", target="target", required=False),
            *(
                RouteEdge(
                    source=node.node_id,
                    target="target",
                    required=False,
                )
                for node in dominated_nodes
            ),
        ),
    )
    duplicates = tuple(
        RouteCandidate(
            candidate_id=f"dup-{index:02d}",
            node_ids=("best", "target"),
        )
        for index in range(32)
    )
    dominated = tuple(
        RouteCandidate(
            candidate_id=f"route-{index:02d}",
            node_ids=(f"dominated-{index:02d}", "target"),
        )
        for index in range(32)
    )
    candidates = (*duplicates, *dominated)
    reduction = reduce_frontier(route_request("sparse"), graph, candidates)
    selection = select_fastest_valid_route(
        route_request("sparse"),
        graph,
        candidates,
    )
    result = {
        "input_candidates": len(candidates),
        "active_candidates": reduction.active_candidate_count,
        "pruned_candidates": len(reduction.pruned_candidates),
        "downstream_evaluations_avoided": (
            len(candidates) - reduction.active_candidate_count
        ),
        "selected_candidate_id": selection.selected_candidate_id,
    }
    return result, (graph, candidates)


def benchmark_dense_parallel() -> dict[str, Any]:
    workers = tuple(
        RouteNode(
            node_id=f"worker-{index:02d}",
            kind=RouteNodeKind.TOOL,
            estimate=RouteEstimate(
                execution_ms=10 + index,
                evidence_strength=100,
                version="benchmark-v1",
            ),
            owned_resources=(f"resource-{index:02d}",),
        )
        for index in range(16)
    )
    target = RouteNode(
        node_id="target",
        kind=RouteNodeKind.OUTCOME,
        estimate=RouteEstimate(
            execution_ms=1,
            evidence_strength=100,
            version="benchmark-v1",
        ),
    )
    graph = RouteGraph(
        graph_id="dense-parallel",
        graph_version="1",
        target_node_id="target",
        nodes=(*workers, target),
        edges=tuple(
            RouteEdge(source=node.node_id, target="target")
            for node in workers
        ),
    )
    candidate = RouteCandidate(
        candidate_id="parallel-route",
        node_ids=tuple(node.node_id for node in workers) + ("target",),
    )
    selection = select_fastest_valid_route(
        route_request("dense"),
        graph,
        (candidate,),
    )
    sequential = sum(
        node.estimate.expected_duration_ms for node in (*workers, target)
    )
    return {
        "sequential_completion_ms": sequential,
        "selected_completion_ms": selection.estimated_completion_ms,
        "estimated_ms_avoided": sequential - selection.estimated_completion_ms,
        "parallel_group_count": len(selection.parallel_groups),
    }


def benchmark_human_delay() -> dict[str, Any]:
    nodes = (
        RouteNode(
            node_id="fast-local",
            kind=RouteNodeKind.MODEL,
            estimate=RouteEstimate(
                execution_ms=1,
                evidence_strength=100,
                version="benchmark-v1",
            ),
        ),
        RouteNode(
            node_id="human-approval",
            kind=RouteNodeKind.APPROVAL,
            estimate=RouteEstimate(
                human_wait_ms=5000,
                evidence_strength=100,
                version="benchmark-v1",
            ),
        ),
        RouteNode(
            node_id="slow-direct",
            kind=RouteNodeKind.MODEL,
            estimate=RouteEstimate(
                execution_ms=100,
                evidence_strength=100,
                version="benchmark-v1",
            ),
        ),
        RouteNode(
            node_id="target",
            kind=RouteNodeKind.OUTCOME,
            estimate=RouteEstimate(
                execution_ms=1,
                evidence_strength=100,
                version="benchmark-v1",
            ),
        ),
    )
    graph = RouteGraph(
        graph_id="human-delay",
        graph_version="1",
        target_node_id="target",
        nodes=nodes,
        edges=(
            RouteEdge(source="fast-local", target="human-approval"),
            RouteEdge(source="human-approval", target="target", required=False),
            RouteEdge(source="slow-direct", target="target", required=False),
        ),
    )
    fast = RouteCandidate(
        candidate_id="fast-local-with-human",
        node_ids=("fast-local", "human-approval", "target"),
    )
    slow = RouteCandidate(
        candidate_id="slow-end-to-end",
        node_ids=("slow-direct", "target"),
    )
    request = route_request("human-delay")
    selection = select_fastest_valid_route(request, graph, (fast, slow))
    fast_only = select_fastest_valid_route(request, graph, (fast,))
    return {
        "selected_candidate_id": selection.selected_candidate_id,
        "selected_completion_ms": selection.estimated_completion_ms,
        "local_fast_route_completion_ms": fast_only.estimated_completion_ms,
    }


def benchmark_semantic_integrity() -> dict[str, Any]:
    failed = RouteConstraint(
        constraint_id="semantic:failed",
        kind=ConstraintKind.SEMANTIC_INTEGRITY,
        satisfied=False,
        evidence_refs=("evidence:semantic-failure",),
    )
    valid = RouteConstraint(
        constraint_id="semantic:valid",
        kind=ConstraintKind.SEMANTIC_INTEGRITY,
        satisfied=True,
        evidence_refs=("evidence:semantic-valid",),
    )
    graph = RouteGraph(
        graph_id="semantic",
        graph_version="1",
        target_node_id="target",
        nodes=(
            RouteNode(
                node_id="fast-invalid",
                kind=RouteNodeKind.MODEL,
                estimate=RouteEstimate(
                    execution_ms=1,
                    evidence_strength=100,
                    version="benchmark-v1",
                ),
                constraints=(failed,),
            ),
            RouteNode(
                node_id="semantic-valid",
                kind=RouteNodeKind.MODEL,
                estimate=RouteEstimate(
                    execution_ms=20,
                    evidence_strength=100,
                    version="benchmark-v1",
                ),
                constraints=(valid,),
            ),
            RouteNode(
                node_id="target",
                kind=RouteNodeKind.OUTCOME,
                estimate=RouteEstimate(evidence_strength=100),
            ),
        ),
        edges=(
            RouteEdge(source="fast-invalid", target="target", required=False),
            RouteEdge(source="semantic-valid", target="target", required=False),
        ),
    )
    selection = select_fastest_valid_route(
        route_request("semantic"),
        graph,
        (
            RouteCandidate(
                candidate_id="fast-invalid",
                node_ids=("fast-invalid", "target"),
            ),
            RouteCandidate(
                candidate_id="semantic-valid",
                node_ids=("semantic-valid", "target"),
            ),
        ),
    )
    invalid = next(
        item
        for item in selection.pruned_candidates
        if item.candidate_id == "fast-invalid"
    )
    return {
        "selected_candidate_id": selection.selected_candidate_id,
        "fast_invalid_reason": invalid.reasons[0].value,
    }


def benchmark_recovery() -> dict[str, Any]:
    graph = RouteGraph(
        graph_id="recovery",
        graph_version="1",
        target_node_id="restored",
        nodes=(
            RouteNode(
                node_id="retry",
                kind=RouteNodeKind.TOOL,
                estimate=RouteEstimate(execution_ms=1, evidence_strength=100),
            ),
            RouteNode(
                node_id="alternate",
                kind=RouteNodeKind.TOOL,
                estimate=RouteEstimate(execution_ms=20, evidence_strength=100),
            ),
            RouteNode(
                node_id="rollback",
                kind=RouteNodeKind.EXECUTION,
                estimate=RouteEstimate(execution_ms=30, evidence_strength=100),
            ),
            RouteNode(
                node_id="restored",
                kind=RouteNodeKind.OUTCOME,
                estimate=RouteEstimate(evidence_strength=100),
            ),
        ),
        edges=(
            RouteEdge(source="retry", target="restored", required=False),
            RouteEdge(source="alternate", target="restored", required=False),
            RouteEdge(source="rollback", target="restored", required=False),
        ),
    )
    options = (
        RecoveryRouteOption(
            option_id="retry",
            mode=RecoveryMode.RETRY,
            candidate=RouteCandidate(
                candidate_id="recovery:retry",
                node_ids=("retry", "restored"),
            ),
            attempts_used=2,
            max_attempts=2,
            evidence_refs=("evidence:retry",),
        ),
        RecoveryRouteOption(
            option_id="alternate",
            mode=RecoveryMode.ALTERNATE_PROVIDER,
            candidate=RouteCandidate(
                candidate_id="recovery:alternate",
                node_ids=("alternate", "restored"),
            ),
            evidence_refs=("evidence:alternate",),
        ),
        RecoveryRouteOption(
            option_id="rollback",
            mode=RecoveryMode.ROLLBACK,
            candidate=RouteCandidate(
                candidate_id="recovery:rollback",
                node_ids=("rollback", "restored"),
            ),
            evidence_refs=("evidence:rollback",),
        ),
    )
    plan = select_recovery_route(
        request=route_request("recovery"),
        graph=graph,
        options=options,
    )
    retry = next(
        item
        for item in plan.recovery_pruned
        if item.candidate_id == "recovery:retry"
    )
    return {
        "selected_mode": plan.selected_mode.value,
        "safe_halt": plan.safe_halt,
        "retry_reason": retry.reasons[0].value,
    }


def benchmark_determinism() -> dict[str, Any]:
    graph = RouteGraph(
        graph_id="determinism",
        graph_version="1",
        target_node_id="target",
        nodes=(
            RouteNode(
                node_id="best",
                kind=RouteNodeKind.MODEL,
                estimate=RouteEstimate(execution_ms=5, evidence_strength=100),
            ),
            RouteNode(
                node_id="second",
                kind=RouteNodeKind.MODEL,
                estimate=RouteEstimate(execution_ms=10, evidence_strength=100),
            ),
            RouteNode(
                node_id="third",
                kind=RouteNodeKind.MODEL,
                estimate=RouteEstimate(execution_ms=15, evidence_strength=100),
            ),
            RouteNode(
                node_id="target",
                kind=RouteNodeKind.OUTCOME,
                estimate=RouteEstimate(evidence_strength=100),
            ),
        ),
        edges=(
            RouteEdge(source="best", target="target", required=False),
            RouteEdge(source="second", target="target", required=False),
            RouteEdge(source="third", target="target", required=False),
        ),
    )
    candidates = (
        RouteCandidate(candidate_id="best", node_ids=("best", "target")),
        RouteCandidate(candidate_id="best-copy", node_ids=("best", "target")),
        RouteCandidate(candidate_id="second", node_ids=("second", "target")),
        RouteCandidate(candidate_id="third", node_ids=("third", "target")),
    )
    digests = {
        select_fastest_valid_route(
            route_request("determinism"),
            graph,
            permutation,
        ).route_digest
        for permutation in itertools.permutations(candidates)
    }
    return {
        "permutations_checked": 24,
        "unique_route_digests": len(digests),
    }


def run_benchmarks(iterations: int = 25) -> dict[str, Any]:
    sparse, sparse_fixture = benchmark_sparse_frontier()
    sparse_graph, sparse_candidates = sparse_fixture
    samples = []
    for _ in range(iterations):
        started = perf_counter_ns()
        select_fastest_valid_route(
            route_request("sparse"),
            sparse_graph,
            sparse_candidates,
        )
        samples.append(perf_counter_ns() - started)
    return {
        "schema_version": "action-frontier-benchmark.v1",
        "structural": {
            "sparse_frontier": sparse,
            "dense_parallel": benchmark_dense_parallel(),
            "human_delay": benchmark_human_delay(),
            "semantic_integrity": benchmark_semantic_integrity(),
            "recovery": benchmark_recovery(),
            "determinism": benchmark_determinism(),
        },
        "timing": {
            "iterations": iterations,
            "median_planning_ns": int(statistics.median(samples)),
            "min_planning_ns": min(samples),
            "max_planning_ns": max(samples),
            "environment_dependent": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=25)
    parser.add_argument("--check", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.iterations < 1:
        raise SystemExit("iterations must be positive")

    result = run_benchmarks(args.iterations)
    serialized = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")

    if args.check:
        expected = json.loads(args.check.read_text(encoding="utf-8"))
        if result["structural"] != expected["structural"]:
            print("structural benchmark mismatch", file=sys.stderr)
            print(
                json.dumps(
                    {
                        "expected": expected["structural"],
                        "actual": result["structural"],
                    },
                    indent=2,
                    sort_keys=True,
                ),
                file=sys.stderr,
            )
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
