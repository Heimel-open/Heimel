"""Deterministic end-to-end route estimates and collision-safe scheduling."""

from __future__ import annotations

from typing import Dict, Iterable, List, Set, Tuple

from src.valo_platform.route_optimization.contracts import (
    RouteCandidate,
    RouteMetrics,
)
from src.valo_platform.route_optimization.graph import RouteGraph


def _partition_ready_nodes(
    ready: Iterable[str],
    resources: Dict[str, Set[str]],
) -> Tuple[Tuple[str, ...], ...]:
    """Partition a ready set into deterministic non-colliding parallel groups."""
    groups: List[List[str]] = []
    group_resources: List[Set[str]] = []
    for node_id in sorted(ready):
        node_resources = resources[node_id]
        placed = False
        for index, used in enumerate(group_resources):
            if node_resources.isdisjoint(used):
                groups[index].append(node_id)
                used.update(node_resources)
                placed = True
                break
        if not placed:
            groups.append([node_id])
            group_resources.append(set(node_resources))
    return tuple(tuple(group) for group in groups)


def estimate_candidate(
    graph: RouteGraph,
    candidate: RouteCandidate,
    completed_nodes: Iterable[str] = (),
) -> RouteMetrics:
    """Estimate governed completion using dependencies and resource collisions."""
    selected = set(candidate.node_ids)
    original_completed = set(completed_nodes) & selected
    completed = set(original_completed)
    node_map = graph.node_map()
    resources = {
        node_id: set(node_map[node_id].owned_resources)
        for node_id in selected
    }

    remaining = selected - completed
    parallel_groups: List[Tuple[str, ...]] = []
    critical_path: List[str] = []
    completion_ms = 0

    while remaining:
        ready = [
            node_id
            for node_id in remaining
            if set(graph.dependency_predecessors(node_id, selected)) <= completed
        ]
        if not ready:
            raise ValueError("candidate cannot be scheduled from current state")

        for group in _partition_ready_nodes(ready, resources):
            parallel_groups.append(group)
            duration_node = max(
                group,
                key=lambda node_id: (
                    node_map[node_id].estimate.expected_duration_ms,
                    node_id,
                ),
            )
            group_duration = node_map[duration_node].estimate.expected_duration_ms
            completion_ms += group_duration
            critical_path.append(duration_node)
            completed.update(group)
            remaining.difference_update(group)

    total_cost = sum(
        node_map[node_id].estimate.cost_microunits
        for node_id in selected
    )
    max_risk = max(
        (node_map[node_id].estimate.risk_exposure for node_id in selected),
        default=0,
    )
    min_reversibility = min(
        (node_map[node_id].estimate.reversibility for node_id in selected),
        default=100,
    )
    min_evidence = min(
        (node_map[node_id].estimate.evidence_strength for node_id in selected),
        default=100,
    )
    active_frontier = tuple(
        sorted(
            node_id
            for node_id in selected - original_completed
            if set(graph.dependency_predecessors(node_id, selected))
            <= original_completed
        )
    )
    estimate_versions = tuple(
        sorted(
            {
                node_map[node_id].estimate.version
                for node_id in selected
            }
        )
    )
    return RouteMetrics(
        completion_ms=completion_ms,
        total_cost_microunits=total_cost,
        max_risk_exposure=max_risk,
        min_reversibility=min_reversibility,
        min_evidence_strength=min_evidence,
        critical_path=tuple(critical_path),
        parallel_groups=tuple(parallel_groups),
        active_frontier=active_frontier,
        estimate_versions=estimate_versions,
    )


def objective_key(metrics: RouteMetrics, candidate_digest: str) -> Tuple[object, ...]:
    """Lexicographic objective: validity is handled before this function."""
    return (
        metrics.completion_ms,
        metrics.total_cost_microunits,
        metrics.max_risk_exposure,
        -metrics.min_reversibility,
        -metrics.min_evidence_strength,
        candidate_digest,
    )


def dominates(left: RouteMetrics, right: RouteMetrics) -> bool:
    """Return True when left Pareto-dominates right."""
    weakly_better = (
        left.completion_ms <= right.completion_ms
        and left.total_cost_microunits <= right.total_cost_microunits
        and left.max_risk_exposure <= right.max_risk_exposure
        and left.min_reversibility >= right.min_reversibility
        and left.min_evidence_strength >= right.min_evidence_strength
    )
    strictly_better = (
        left.completion_ms < right.completion_ms
        or left.total_cost_microunits < right.total_cost_microunits
        or left.max_risk_exposure < right.max_risk_exposure
        or left.min_reversibility > right.min_reversibility
        or left.min_evidence_strength > right.min_evidence_strength
    )
    return weakly_better and strictly_better


__all__ = ["dominates", "estimate_candidate", "objective_key"]
