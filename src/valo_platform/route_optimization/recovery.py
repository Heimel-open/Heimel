"""Recovery candidates use the same fastest-valid-route selector."""

from __future__ import annotations

from enum import Enum
from typing import Iterable, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.valo_platform.canonical import canonical_digest
from src.valo_platform.route_optimization.contracts import (
    PrunedCandidate,
    RouteCandidate,
    RouteRequest,
    RouteSelection,
    SelectionStatus,
)
from src.valo_platform.route_optimization.graph import RouteGraph
from src.valo_platform.route_optimization.reason_codes import RouteReasonCode
from src.valo_platform.route_optimization.selector import (
    select_fastest_valid_route,
)


class RecoveryMode(str, Enum):
    RETRY = "RETRY"
    ALTERNATE_PROVIDER = "ALTERNATE_PROVIDER"
    ROLLBACK = "ROLLBACK"
    DEGRADED = "DEGRADED"


class RecoveryRouteOption(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    option_id: str
    mode: RecoveryMode
    candidate: RouteCandidate
    available: bool = True
    restores_valid_state: bool = True
    attempts_used: int = Field(default=0, ge=0)
    max_attempts: int = Field(default=1, ge=0)
    evidence_refs: tuple[str, ...] = ()
    detail: str = ""

    @model_validator(mode="after")
    def _candidate_identity_must_be_unique_to_option(self) -> "RecoveryRouteOption":
        if not self.option_id or not self.candidate.candidate_id:
            raise ValueError("recovery option and candidate identities are required")
        return self


class RecoveryPlan(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    selected_option_id: Optional[str] = None
    selected_mode: Optional[RecoveryMode] = None
    route_selection: RouteSelection
    recovery_pruned: tuple[PrunedCandidate, ...] = ()
    safe_halt: bool
    blockers: tuple[RouteReasonCode, ...]
    plan_digest: str

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.model_copy(update={"plan_digest": ""}))


def select_recovery_route(
    *,
    request: RouteRequest,
    graph: RouteGraph,
    options: Iterable[RecoveryRouteOption],
    completed_nodes: Iterable[str] = (),
) -> RecoveryPlan:
    ordered = tuple(sorted(options, key=lambda item: item.option_id))
    candidate_ids = [item.candidate.candidate_id for item in ordered]
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("recovery options contain duplicate candidate identities")

    eligible = []
    pre_pruned = []
    by_candidate = {}
    for option in ordered:
        reason = None
        detail = option.detail
        if not option.available or not option.restores_valid_state:
            reason = RouteReasonCode.ROUTE_RECOVERY_UNAVAILABLE
            detail = detail or "recovery option cannot restore a valid state"
        elif (
            option.mode is RecoveryMode.RETRY
            and option.attempts_used >= option.max_attempts
        ):
            reason = RouteReasonCode.ROUTE_RETRY_EXHAUSTED
            detail = detail or "retry budget exhausted"

        if reason is not None:
            pre_pruned.append(
                PrunedCandidate(
                    candidate_id=option.candidate.candidate_id,
                    reasons=(reason,),
                    detail=detail,
                )
            )
            continue
        eligible.append(option.candidate)
        by_candidate[option.candidate.candidate_id] = option

    selection = select_fastest_valid_route(
        request=request,
        graph=graph,
        candidates=tuple(eligible),
        completed_nodes=completed_nodes,
    )
    recovery_pruned = tuple(
        sorted(
            (*pre_pruned, *selection.pruned_candidates),
            key=lambda item: item.candidate_id,
        )
    )

    if selection.status is SelectionStatus.NO_ROUTE:
        blockers = tuple(
            sorted(
                set(selection.blockers)
                | {
                    reason
                    for item in pre_pruned
                    for reason in item.reasons
                }
                | {RouteReasonCode.ROUTE_RECOVERY_UNAVAILABLE},
                key=lambda item: item.value,
            )
        )
        route_selection = selection.model_copy(
            update={"pruned_candidates": recovery_pruned, "blockers": blockers}
        )
        provisional = RecoveryPlan(
            route_selection=route_selection,
            recovery_pruned=recovery_pruned,
            safe_halt=True,
            blockers=blockers,
            plan_digest="",
        )
    else:
        option = by_candidate[selection.selected_candidate_id]
        route_selection = selection.model_copy(
            update={"pruned_candidates": recovery_pruned}
        )
        provisional = RecoveryPlan(
            selected_option_id=option.option_id,
            selected_mode=option.mode,
            route_selection=route_selection,
            recovery_pruned=recovery_pruned,
            safe_halt=False,
            blockers=(),
            plan_digest="",
        )
    return provisional.model_copy(
        update={"plan_digest": provisional.computed_digest}
    )


__all__ = [
    "RecoveryMode",
    "RecoveryPlan",
    "RecoveryRouteOption",
    "select_recovery_route",
]
