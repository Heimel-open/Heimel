"""Frontier reduction, duplicate elimination, pivots and Pareto pruning."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from pydantic import BaseModel, ConfigDict

from src.valo_platform.canonical import canonical_digest
from src.valo_platform.route_optimization.constraints import validate_candidate
from src.valo_platform.route_optimization.contracts import (
    PrunedCandidate,
    RouteCandidate,
    RouteMetrics,
    RoutePivot,
    RouteRequest,
)
from src.valo_platform.route_optimization.estimates import dominates, estimate_candidate
from src.valo_platform.route_optimization.graph import RouteGraph
from src.valo_platform.route_optimization.reason_codes import RouteReasonCode


class EvaluatedRoute(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    candidate: RouteCandidate
    metrics: RouteMetrics


class FrontierReduction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    active_candidates: Tuple[EvaluatedRoute, ...]
    pruned_candidates: Tuple[PrunedCandidate, ...]
    pivots: Tuple[RoutePivot, ...]
    input_candidate_count: int
    active_candidate_count: int


def _make_pivots(
    active: Iterable[EvaluatedRoute],
) -> Tuple[RoutePivot, ...]:
    grouped: Dict[Tuple[str, ...], List[str]] = defaultdict(list)
    for evaluated in active:
        grouped[evaluated.metrics.active_frontier].append(
            evaluated.candidate.candidate_id
        )

    pivots = []
    for frontier, candidate_ids in sorted(grouped.items()):
        sorted_ids = tuple(sorted(candidate_ids))
        pivot_id = canonical_digest(
            {
                "active_frontier": frontier,
                "candidate_ids": sorted_ids,
            }
        )
        pivots.append(
            RoutePivot(
                pivot_id=pivot_id,
                active_frontier=frontier,
                candidate_ids=sorted_ids,
            )
        )
    return tuple(pivots)


def reduce_frontier(
    request: RouteRequest,
    graph: RouteGraph,
    candidates: Iterable[RouteCandidate],
    completed_nodes: Iterable[str] = (),
) -> FrontierReduction:
    ordered_candidates = tuple(
        sorted(candidates, key=lambda candidate: candidate.candidate_id)
    )
    pruned: List[PrunedCandidate] = []
    valid: List[EvaluatedRoute] = []
    seen_fingerprints: Dict[str, str] = {}

    for candidate in ordered_candidates:
        validity = validate_candidate(request, graph, candidate)
        if not validity.valid:
            pruned.append(
                PrunedCandidate(
                    candidate_id=candidate.candidate_id,
                    reasons=validity.reasons,
                    detail=validity.detail,
                )
            )
            continue

        fingerprint = candidate.route_signature
        if fingerprint in seen_fingerprints:
            pruned.append(
                PrunedCandidate(
                    candidate_id=candidate.candidate_id,
                    reasons=(RouteReasonCode.ROUTE_DUPLICATE,),
                    detail="candidate is canonically identical",
                    dominated_by=seen_fingerprints[fingerprint],
                )
            )
            continue
        seen_fingerprints[fingerprint] = candidate.candidate_id

        metrics = estimate_candidate(
            graph,
            candidate,
            completed_nodes=completed_nodes,
        )
        if (
            request.deadline_ms is not None
            and metrics.completion_ms > request.deadline_ms
        ):
            pruned.append(
                PrunedCandidate(
                    candidate_id=candidate.candidate_id,
                    reasons=(RouteReasonCode.ROUTE_DEADLINE_UNREACHABLE,),
                    detail="estimated completion exceeds deadline",
                )
            )
            continue
        valid.append(EvaluatedRoute(candidate=candidate, metrics=metrics))

    dominated_ids = set()
    for right in valid:
        for left in valid:
            if left.candidate.candidate_id == right.candidate.candidate_id:
                continue
            if dominates(left.metrics, right.metrics):
                dominated_ids.add(right.candidate.candidate_id)
                pruned.append(
                    PrunedCandidate(
                        candidate_id=right.candidate.candidate_id,
                        reasons=(RouteReasonCode.ROUTE_DOMINATED,),
                        detail="candidate is Pareto-dominated",
                        dominated_by=left.candidate.candidate_id,
                    )
                )
                break

    active = tuple(
        sorted(
            (
                evaluated
                for evaluated in valid
                if evaluated.candidate.candidate_id not in dominated_ids
            ),
            key=lambda item: item.candidate.candidate_id,
        )
    )
    return FrontierReduction(
        active_candidates=active,
        pruned_candidates=tuple(
            sorted(pruned, key=lambda item: item.candidate_id)
        ),
        pivots=_make_pivots(active),
        input_candidate_count=len(ordered_candidates),
        active_candidate_count=len(active),
    )


__all__ = ["EvaluatedRoute", "FrontierReduction", "reduce_frontier"]
