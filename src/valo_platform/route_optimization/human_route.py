"""Human step-up routing to the correct authority holder."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Iterable, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.valo_platform.canonical import canonical_digest
from src.valo_platform.route_optimization.contracts import (
    ConstraintKind,
    RouteConstraint,
    RouteEstimate,
    RouteNode,
    RouteNodeKind,
)
from src.valo_platform.route_optimization.reason_codes import RouteReasonCode


class HumanRouteStatus(str, Enum):
    ROUTED = "ROUTED"
    DEFER = "DEFER"
    SAFE_HALT = "SAFE_HALT"


class AuthorityHolder(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    holder_id: str
    principal_id: str
    authority_scopes: tuple[str, ...]
    active: bool = True
    available_at: datetime
    mandate_expires_at: datetime
    expected_response_ms: int = Field(default=0, ge=0)
    evidence_refs: tuple[str, ...]

    @field_validator("authority_scopes", mode="before")
    @classmethod
    def _require_scopes(cls, value: object) -> object:
        values = tuple(sorted(set(value or ())))
        if not values:
            raise ValueError("authority holder requires at least one scope")
        return values

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def _require_authority_evidence(cls, value: object) -> object:
        values = tuple(sorted(set(value or ())))
        if not values:
            raise ValueError("authority holder requires evidence")
        return values


class HumanStepUpRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    step_up_id: str
    route_request_id: str
    route_digest: str
    route_version: str
    action_ref: str
    action_payload_digest: str
    required_authority_scope: str
    evidence_refs: tuple[str, ...]
    requested_at: datetime
    deadline: datetime
    max_wait_ms: Optional[int] = Field(default=None, ge=0)

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def _require_evidence(cls, value: object) -> object:
        values = tuple(sorted(set(value or ())))
        if not values:
            raise ValueError("step-up request requires evidence")
        return values


class HumanStepUpRoute(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: HumanRouteStatus
    selected_holder_id: Optional[str] = None
    selected_principal_id: Optional[str] = None
    expected_wait_ms: Optional[int] = Field(default=None, ge=0)
    approval_node: Optional[RouteNode] = None
    evidence_bundle_digest: str
    blockers: tuple[RouteReasonCode, ...] = ()
    route_digest: str

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.model_copy(update={"route_digest": ""}))


def _wait_ms(requested_at: datetime, holder: AuthorityHolder) -> int:
    availability_delay = max(
        0,
        int((holder.available_at - requested_at).total_seconds() * 1000),
    )
    return availability_delay + holder.expected_response_ms


def route_human_step_up(
    *,
    request: HumanStepUpRequest,
    holders: Iterable[AuthorityHolder],
) -> HumanStepUpRoute:
    if request.deadline <= request.requested_at:
        status = HumanRouteStatus.SAFE_HALT
        blockers = (RouteReasonCode.ROUTE_DEADLINE_UNREACHABLE,)
        bundle_digest = canonical_digest(
            {"request": request, "eligible_holders": ()}
        )
        provisional = HumanStepUpRoute(
            status=status,
            evidence_bundle_digest=bundle_digest,
            blockers=blockers,
            route_digest="",
        )
        return provisional.model_copy(
            update={"route_digest": provisional.computed_digest}
        )

    ordered = tuple(sorted(holders, key=lambda item: item.holder_id))
    scope_holders = tuple(
        holder
        for holder in ordered
        if holder.active
        and request.required_authority_scope in holder.authority_scopes
        and holder.mandate_expires_at > request.requested_at
    )
    eligible = []
    for holder in scope_holders:
        wait_ms = _wait_ms(request.requested_at, holder)
        completion = request.requested_at + timedelta(milliseconds=wait_ms)
        within_max_wait = (
            request.max_wait_ms is None or wait_ms <= request.max_wait_ms
        )
        if (
            completion <= request.deadline
            and completion < holder.mandate_expires_at
            and within_max_wait
        ):
            eligible.append((wait_ms, holder))

    bundle_digest = canonical_digest(
        {
            "request": request,
            "authority_evidence": tuple(
                (
                    holder.holder_id,
                    holder.principal_id,
                    holder.authority_scopes,
                    holder.evidence_refs,
                    holder.mandate_expires_at,
                )
                for holder in ordered
            ),
        }
    )

    if not eligible:
        if not scope_holders:
            status = HumanRouteStatus.SAFE_HALT
            blockers = (
                RouteReasonCode.ROUTE_AUTHORITY_HOLDER_UNAVAILABLE,
            )
        else:
            status = HumanRouteStatus.DEFER
            blockers = (
                RouteReasonCode.ROUTE_REPLAN_DEFERRED,
                RouteReasonCode.ROUTE_REQUIRES_STEP_UP,
            )
        provisional = HumanStepUpRoute(
            status=status,
            evidence_bundle_digest=bundle_digest,
            blockers=blockers,
            route_digest="",
        )
        return provisional.model_copy(
            update={"route_digest": provisional.computed_digest}
        )

    wait_ms, holder = min(
        eligible,
        key=lambda item: (item[0], item[1].principal_id, item[1].holder_id),
    )
    combined_evidence = tuple(
        sorted(set(request.evidence_refs) | set(holder.evidence_refs))
    )
    approval_node = RouteNode(
        node_id=f"human-step-up:{request.step_up_id}",
        kind=RouteNodeKind.APPROVAL,
        estimate=RouteEstimate(
            human_wait_ms=wait_ms,
            evidence_strength=100,
            source_ref=f"authority-holder:{holder.holder_id}",
            version="human-step-up.v1",
        ),
        constraints=(
            RouteConstraint(
                constraint_id=f"human-authority:{holder.holder_id}",
                kind=ConstraintKind.HUMAN_CHECKPOINT,
                satisfied=True,
                evidence_refs=combined_evidence,
                detail=(
                    "exact authority scope bound to human step-up route"
                ),
            ),
        ),
        evidence_refs=combined_evidence,
        owner_ref=holder.principal_id,
        owned_resources=(f"authority-holder:{holder.holder_id}",),
        mandatory_governance=True,
    )
    provisional = HumanStepUpRoute(
        status=HumanRouteStatus.ROUTED,
        selected_holder_id=holder.holder_id,
        selected_principal_id=holder.principal_id,
        expected_wait_ms=wait_ms,
        approval_node=approval_node,
        evidence_bundle_digest=bundle_digest,
        blockers=(),
        route_digest="",
    )
    return provisional.model_copy(
        update={"route_digest": provisional.computed_digest}
    )


__all__ = [
    "AuthorityHolder",
    "HumanRouteStatus",
    "HumanStepUpRequest",
    "HumanStepUpRoute",
    "route_human_step_up",
]
