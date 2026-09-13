"""Runtime glue for the autonomous commercial loop.

This module turns observed inbound events and already-accepted commercial scope
into deterministic Factory OS state transitions/build orders. It never parses a
message as contractual acceptance and never executes an external side effect.
"""

from __future__ import annotations

from dataclasses import dataclass

from lib.commercial_channels import ChannelDirection, CommercialChannelEvent
from lib.commercial_loop import CommercialLoop, CommercialState
from lib.commercial_missions import (
    CommercialMissionKind,
    CommercialMissionSpec,
    build_order_from_commercial_spec,
)


@dataclass(frozen=True)
class ServiceCheckResult:
    service_ref: str
    check_ref: str
    healthy: bool
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.service_ref.strip() or not self.check_ref.strip():
            raise ValueError("service_ref and check_ref are required")
        if not self.evidence_refs:
            raise ValueError("service checks require evidence_refs")


class CommercialRuntime:
    """Deterministic commercial-loop coordinator with no authority surface."""

    def observe_inbound(
        self,
        loop: CommercialLoop,
        event: CommercialChannelEvent,
    ) -> CommercialState:
        if event.direction is not ChannelDirection.INBOUND:
            raise ValueError("only inbound channel events are observations")

        if loop.state is CommercialState.OUTREACH_SENT:
            target = CommercialState.RESPONSE_OBSERVED
        elif loop.state is CommercialState.CUSTOMER_ACTIVE:
            target = CommercialState.SERVICE_SIGNAL_OBSERVED
        else:
            raise ValueError(f"inbound event is not valid from {loop.state.value}")

        loop.transition(target, evidence_refs=[event.event_ref])
        return loop.state

    def create_build_mission(
        self,
        loop: CommercialLoop,
        spec: CommercialMissionSpec,
        *,
        principal: str,
        authority_basis: str,
    ):
        order = build_order_from_commercial_spec(
            loop,
            spec,
            principal=principal,
            authority_basis=authority_basis,
        )
        target = {
            CommercialMissionKind.POC: CommercialState.POC_MISSION_CREATED,
            CommercialMissionKind.PRODUCTION: CommercialState.PRODUCTION_MISSION_CREATED,
            CommercialMissionKind.SUPPORT: CommercialState.SUPPORT_MISSION_CREATED,
        }[spec.kind]
        loop.transition(target, evidence_refs=[order.build_order_id, spec.spec_ref])
        return order

    def observe_service_check(
        self,
        loop: CommercialLoop,
        result: ServiceCheckResult,
    ) -> CommercialState:
        if loop.state is not CommercialState.CUSTOMER_ACTIVE:
            raise ValueError("service checks are actionable only for active customers")
        if result.healthy:
            return loop.state
        loop.transition(
            CommercialState.SERVICE_SIGNAL_OBSERVED,
            evidence_refs=(result.check_ref, *result.evidence_refs),
        )
        return loop.state

    @property
    def has_authority_surface(self) -> bool:
        return False


__all__ = ["CommercialRuntime", "ServiceCheckResult"]
