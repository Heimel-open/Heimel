"""Material-delta detection, bounded replanning and route invalidation."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Iterable, Optional

from pydantic import BaseModel, ConfigDict, Field

from src.valo_platform.canonical import canonical_digest
from src.valo_platform.route_optimization.contracts import RouteSelection
from src.valo_platform.route_optimization.reason_codes import RouteReasonCode


class MaterialDeltaKind(str, Enum):
    AUTHORITY = "authority"
    POLICY = "policy"
    CONTEXT = "context"
    EVIDENCE = "evidence"
    MAL = "mal"
    VAIG = "vaig"
    DEPENDENCY = "dependency"
    COST = "cost"
    CAPACITY = "capacity"
    DEADLINE = "deadline"
    HUMAN_AVAILABILITY = "human_availability"
    EXECUTION_STATE = "execution_state"
    ACTION_PAYLOAD = "action_payload"


_CRITICAL_DELTAS = {
    MaterialDeltaKind.AUTHORITY,
    MaterialDeltaKind.POLICY,
    MaterialDeltaKind.CONTEXT,
    MaterialDeltaKind.EVIDENCE,
    MaterialDeltaKind.MAL,
    MaterialDeltaKind.VAIG,
    MaterialDeltaKind.EXECUTION_STATE,
    MaterialDeltaKind.ACTION_PAYLOAD,
}


class RouteStateSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    authority_hash: str
    policy_hash: str
    context_hash: str
    evidence_hash: str
    mal_hash: str
    vaig_hash: str
    dependency_hash: str
    cost_snapshot_hash: str
    capacity_hash: str
    deadline_hash: str
    human_availability_hash: str
    execution_state_hash: str
    action_payload_digest: str
    captured_at: datetime

    @property
    def fingerprint(self) -> str:
        return canonical_digest(self)


class MaterialDelta(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    previous_state_fingerprint: str
    current_state_fingerprint: str
    changed: tuple[MaterialDeltaKind, ...]
    critical: bool
    delta_digest: str

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.model_copy(update={"delta_digest": ""}))


class ReplanAction(str, Enum):
    KEEP_CURRENT = "KEEP_CURRENT"
    REPLAN = "REPLAN"
    DEFER = "DEFER"
    SAFE_HALT = "SAFE_HALT"


class ReplanPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    max_replans: int = Field(default=3, ge=0)
    min_interval_ms: int = Field(default=1000, ge=0)


class ReplanTracker(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    route_digest: str
    route_version: str
    replan_count: int = Field(default=0, ge=0)
    last_replan_at: Optional[datetime] = None
    last_delta_digest: Optional[str] = None


class ReplanDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    action: ReplanAction
    reasons: tuple[RouteReasonCode, ...]
    delta: MaterialDelta
    execution_blocked: bool
    next_route_version: Optional[str] = None
    next_tracker: ReplanTracker
    decision_digest: str

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.model_copy(update={"decision_digest": ""}))


class RouteInvalidation(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    route_digest: str
    reason: RouteReasonCode
    affected_node_ids: tuple[str, ...]
    invalidated_at: datetime
    invalidation_digest: str

    @property
    def computed_digest(self) -> str:
        return canonical_digest(
            self.model_copy(update={"invalidation_digest": ""})
        )


def detect_material_delta(
    previous: RouteStateSnapshot,
    current: RouteStateSnapshot,
) -> MaterialDelta:
    field_map = {
        MaterialDeltaKind.AUTHORITY: "authority_hash",
        MaterialDeltaKind.POLICY: "policy_hash",
        MaterialDeltaKind.CONTEXT: "context_hash",
        MaterialDeltaKind.EVIDENCE: "evidence_hash",
        MaterialDeltaKind.MAL: "mal_hash",
        MaterialDeltaKind.VAIG: "vaig_hash",
        MaterialDeltaKind.DEPENDENCY: "dependency_hash",
        MaterialDeltaKind.COST: "cost_snapshot_hash",
        MaterialDeltaKind.CAPACITY: "capacity_hash",
        MaterialDeltaKind.DEADLINE: "deadline_hash",
        MaterialDeltaKind.HUMAN_AVAILABILITY: "human_availability_hash",
        MaterialDeltaKind.EXECUTION_STATE: "execution_state_hash",
        MaterialDeltaKind.ACTION_PAYLOAD: "action_payload_digest",
    }
    changed = tuple(
        sorted(
            (
                kind
                for kind, field_name in field_map.items()
                if getattr(previous, field_name) != getattr(current, field_name)
            ),
            key=lambda item: item.value,
        )
    )
    provisional = MaterialDelta(
        previous_state_fingerprint=previous.fingerprint,
        current_state_fingerprint=current.fingerprint,
        changed=changed,
        critical=any(kind in _CRITICAL_DELTAS for kind in changed),
        delta_digest="",
    )
    return provisional.model_copy(
        update={"delta_digest": provisional.computed_digest}
    )


def decide_replan(
    *,
    previous: RouteStateSnapshot,
    current: RouteStateSnapshot,
    tracker: ReplanTracker,
    policy: ReplanPolicy = ReplanPolicy(),
    now: Optional[datetime] = None,
) -> ReplanDecision:
    current_time = now or current.captured_at
    delta = detect_material_delta(previous, current)

    if not delta.changed:
        action = ReplanAction.KEEP_CURRENT
        reasons: tuple[RouteReasonCode, ...] = ()
        execution_blocked = False
        next_version = None
        next_tracker = tracker
    elif tracker.replan_count >= policy.max_replans:
        action = ReplanAction.SAFE_HALT
        reasons = (RouteReasonCode.ROUTE_REPLAN_BUDGET_EXHAUSTED,)
        execution_blocked = True
        next_version = None
        next_tracker = tracker.model_copy(
            update={"last_delta_digest": delta.delta_digest}
        )
    elif tracker.last_delta_digest == delta.delta_digest:
        action = ReplanAction.DEFER
        reasons = (RouteReasonCode.ROUTE_REPLAN_DEFERRED,)
        execution_blocked = True
        next_version = None
        next_tracker = tracker
    else:
        elapsed_ms = None
        if tracker.last_replan_at is not None:
            elapsed_ms = int(
                (current_time - tracker.last_replan_at).total_seconds() * 1000
            )
        within_cooldown = (
            elapsed_ms is not None and elapsed_ms < policy.min_interval_ms
        )
        if within_cooldown and delta.critical:
            action = ReplanAction.SAFE_HALT
            reasons = (RouteReasonCode.ROUTE_INVALIDATED_BY_DRIFT,)
            execution_blocked = True
            next_version = None
            next_tracker = tracker.model_copy(
                update={"last_delta_digest": delta.delta_digest}
            )
        elif within_cooldown:
            action = ReplanAction.DEFER
            reasons = (RouteReasonCode.ROUTE_REPLAN_DEFERRED,)
            execution_blocked = True
            next_version = None
            next_tracker = tracker.model_copy(
                update={"last_delta_digest": delta.delta_digest}
            )
        else:
            action = ReplanAction.REPLAN
            reasons = (RouteReasonCode.ROUTE_INVALIDATED_BY_DRIFT,)
            execution_blocked = True
            next_version = f"{tracker.route_version}.r{tracker.replan_count + 1}"
            next_tracker = tracker.model_copy(
                update={
                    "route_version": next_version,
                    "replan_count": tracker.replan_count + 1,
                    "last_replan_at": current_time,
                    "last_delta_digest": delta.delta_digest,
                }
            )

    provisional = ReplanDecision(
        action=action,
        reasons=reasons,
        delta=delta,
        execution_blocked=execution_blocked,
        next_route_version=next_version,
        next_tracker=next_tracker,
        decision_digest="",
    )
    return provisional.model_copy(
        update={"decision_digest": provisional.computed_digest}
    )


def invalidate_route(
    *,
    selection: RouteSelection,
    completed_node_ids: Iterable[str] = (),
    invalidated_at: datetime,
    cancelled: bool = False,
    expires_at: Optional[datetime] = None,
) -> RouteInvalidation:
    if not selection.route_digest:
        raise ValueError("route selection has no route digest")
    if cancelled:
        reason = RouteReasonCode.ROUTE_CANCELLED
    elif expires_at is not None and expires_at <= invalidated_at:
        reason = RouteReasonCode.ROUTE_EXPIRED
    else:
        raise ValueError("route is neither cancelled nor expired")
    affected = tuple(
        sorted(set(selection.selected_node_ids) - set(completed_node_ids))
    )
    provisional = RouteInvalidation(
        route_digest=selection.route_digest,
        reason=reason,
        affected_node_ids=affected,
        invalidated_at=invalidated_at,
        invalidation_digest="",
    )
    return provisional.model_copy(
        update={"invalidation_digest": provisional.computed_digest}
    )


__all__ = [
    "MaterialDelta",
    "MaterialDeltaKind",
    "ReplanAction",
    "ReplanDecision",
    "ReplanPolicy",
    "ReplanTracker",
    "RouteInvalidation",
    "RouteStateSnapshot",
    "decide_replan",
    "detect_material_delta",
    "invalidate_route",
]
