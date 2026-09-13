"""Constraint-first validity evaluation for candidate routes."""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from pydantic import BaseModel, ConfigDict

from src.valo_platform.route_optimization.contracts import (
    ConstraintKind,
    RouteCandidate,
    RouteConstraint,
    RouteRequest,
)
from src.valo_platform.route_optimization.graph import RouteGraph
from src.valo_platform.route_optimization.reason_codes import RouteReasonCode


class RouteValidity(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    valid: bool
    reasons: Tuple[RouteReasonCode, ...] = ()
    detail: str = ""
    satisfied_constraint_ids: Tuple[str, ...] = ()
    evidence_refs: Tuple[str, ...] = ()


def _all_constraints(
    graph: RouteGraph, candidate: RouteCandidate
) -> Tuple[RouteConstraint, ...]:
    node_map = graph.node_map()
    constraints = list(candidate.constraints)
    for node_id in candidate.node_ids:
        constraints.extend(node_map[node_id].constraints)
    return tuple(constraints)


def validate_candidate(
    request: RouteRequest,
    graph: RouteGraph,
    candidate: RouteCandidate,
) -> RouteValidity:
    graph_error = graph.candidate_error(candidate)
    if graph_error:
        return RouteValidity(
            valid=False,
            reasons=(RouteReasonCode.ROUTE_DEPENDENCY_UNREACHABLE,),
            detail=graph_error,
        )

    if candidate.valid_until is not None and candidate.valid_until <= request.as_of:
        return RouteValidity(
            valid=False,
            reasons=(RouteReasonCode.ROUTE_STATE_STALE,),
            detail="candidate validity window has expired",
        )

    constraints = _all_constraints(graph, candidate)
    by_kind: Dict[ConstraintKind, List[RouteConstraint]] = {}
    for constraint in constraints:
        by_kind.setdefault(constraint.kind, []).append(constraint)

    reasons: Set[RouteReasonCode] = set()
    details = []
    for kind in request.required_constraint_kinds:
        entries = by_kind.get(kind, [])
        if not entries:
            reason = RouteConstraint(
                constraint_id=f"missing:{kind.value}",
                kind=kind,
                satisfied=False,
            ).failure_reason
            reasons.add(reason)
            details.append(f"missing required constraint: {kind.value}")

    for constraint in constraints:
        if constraint.hard and not constraint.satisfied:
            reasons.add(constraint.failure_reason)
            details.append(
                f"{constraint.constraint_id} failed: "
                f"{constraint.detail or constraint.kind.value}"
            )

    node_map = graph.node_map()
    missing_checkpoints = (
        set(request.required_human_checkpoints) - set(candidate.node_ids)
    )
    if missing_checkpoints:
        reasons.add(RouteReasonCode.ROUTE_HUMAN_CHECKPOINT_MISSING)
        details.append(
            "candidate omits required human checkpoints: "
            f"{sorted(missing_checkpoints)}"
        )

    total_cost = sum(
        node_map[node_id].estimate.cost_microunits
        for node_id in candidate.node_ids
    )
    max_risk = max(
        (node_map[node_id].estimate.risk_exposure for node_id in candidate.node_ids),
        default=0,
    )
    min_reversibility = min(
        (node_map[node_id].estimate.reversibility for node_id in candidate.node_ids),
        default=100,
    )

    if (
        request.budget_limit_microunits is not None
        and total_cost > request.budget_limit_microunits
    ):
        reasons.add(RouteReasonCode.ROUTE_BUDGET_EXCEEDED)
        details.append("candidate exceeds budget limit")

    if (
        request.max_risk_exposure is not None
        and max_risk > request.max_risk_exposure
    ):
        reasons.add(RouteReasonCode.ROUTE_RISK_EXCEEDED)
        details.append("candidate exceeds risk limit")

    if (
        request.min_reversibility is not None
        and min_reversibility < request.min_reversibility
    ):
        reasons.add(RouteReasonCode.ROUTE_IRREVERSIBILITY_EXCEEDED)
        details.append("candidate is below reversibility floor")

    evidence_refs = sorted(
        {
            evidence
            for constraint in constraints
            for evidence in constraint.evidence_refs
        }
        | {
            evidence
            for node_id in candidate.node_ids
            for evidence in node_map[node_id].evidence_refs
        }
    )
    satisfied_ids = sorted(
        constraint.constraint_id
        for constraint in constraints
        if constraint.satisfied
    )

    ordered_reasons = tuple(sorted(reasons, key=lambda reason: reason.value))
    return RouteValidity(
        valid=not ordered_reasons,
        reasons=ordered_reasons,
        detail="; ".join(details),
        satisfied_constraint_ids=tuple(satisfied_ids),
        evidence_refs=tuple(evidence_refs),
    )


__all__ = ["RouteValidity", "validate_candidate"]
