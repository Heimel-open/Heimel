"""Deterministic fastest-valid-route selection."""

from __future__ import annotations

from typing import Iterable, Tuple

from src.valo_platform.canonical import canonical_digest
from src.valo_platform.route_optimization.contracts import (
    RouteCandidate,
    RouteRequest,
    RouteSelection,
    SelectionStatus,
)
from src.valo_platform.route_optimization.estimates import objective_key
from src.valo_platform.route_optimization.frontier import reduce_frontier
from src.valo_platform.route_optimization.graph import RouteGraph
from src.valo_platform.route_optimization.reason_codes import RouteReasonCode


def _blockers(reasons: Iterable[RouteReasonCode]) -> Tuple[RouteReasonCode, ...]:
    ordered = sorted(set(reasons), key=lambda reason: reason.value)
    if not ordered:
        return (RouteReasonCode.ROUTE_NO_VALID_CANDIDATE,)
    return tuple(ordered)


def select_fastest_valid_route(
    request: RouteRequest,
    graph: RouteGraph,
    candidates: Iterable[RouteCandidate],
    completed_nodes: Iterable[str] = (),
) -> RouteSelection:
    reduction = reduce_frontier(
        request=request,
        graph=graph,
        candidates=candidates,
        completed_nodes=completed_nodes,
    )
    if not reduction.active_candidates:
        return RouteSelection(
            status=SelectionStatus.NO_ROUTE,
            route_request_id=request.route_request_id,
            pivot_set=reduction.pivots,
            pruned_candidates=reduction.pruned_candidates,
            blockers=_blockers(
                reason
                for pruned in reduction.pruned_candidates
                for reason in pruned.reasons
            ),
        )

    selected = min(
        reduction.active_candidates,
        key=lambda evaluated: objective_key(
            evaluated.metrics,
            evaluated.candidate.fingerprint,
        ),
    )
    candidate = selected.candidate
    metrics = selected.metrics
    route_payload = {
        "request_fingerprint": request.fingerprint,
        "graph_fingerprint": graph.fingerprint,
        "candidate_fingerprint": candidate.fingerprint,
        "metrics": metrics,
        "completed_nodes": tuple(sorted(set(completed_nodes))),
        "estimate_set_version": request.estimate_set_version,
    }
    route_digest = canonical_digest(route_payload)

    return RouteSelection(
        status=SelectionStatus.SELECTED,
        route_request_id=request.route_request_id,
        selected_candidate_id=candidate.candidate_id,
        selected_node_ids=candidate.node_ids,
        active_frontier=metrics.active_frontier,
        pivot_set=reduction.pivots,
        critical_path=metrics.critical_path,
        parallel_groups=metrics.parallel_groups,
        estimated_completion_ms=metrics.completion_ms,
        estimated_total_cost_microunits=metrics.total_cost_microunits,
        max_risk_exposure=metrics.max_risk_exposure,
        min_reversibility=metrics.min_reversibility,
        min_evidence_strength=metrics.min_evidence_strength,
        estimate_versions=metrics.estimate_versions,
        assumptions=candidate.assumptions,
        pruned_candidates=reduction.pruned_candidates,
        blockers=(),
        valid_until=candidate.valid_until,
        route_digest=route_digest,
    )


__all__ = ["select_fastest_valid_route"]
