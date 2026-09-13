from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .contracts import RetailAction, RetailActionIntentV1


class VehicleLifecycle(str, Enum):
    CANDIDATE = "CANDIDATE"
    PURCHASED = "PURCHASED"
    IN_TRANSIT = "IN_TRANSIT"
    EXPORTED = "EXPORTED"
    LISTED = "LISTED"
    SALE_AGREED = "SALE_AGREED"
    SOLD = "SOLD"


_ACTION_TRANSITIONS: dict[RetailAction, tuple[VehicleLifecycle, VehicleLifecycle]] = {
    RetailAction.VEHICLE_PURCHASE: (VehicleLifecycle.CANDIDATE, VehicleLifecycle.PURCHASED),
    RetailAction.VEHICLE_BOOK_TRANSPORT: (VehicleLifecycle.PURCHASED, VehicleLifecycle.IN_TRANSIT),
    RetailAction.VEHICLE_EXPORT: (VehicleLifecycle.IN_TRANSIT, VehicleLifecycle.EXPORTED),
    RetailAction.VEHICLE_LIST_SALE: (VehicleLifecycle.EXPORTED, VehicleLifecycle.LISTED),
    RetailAction.VEHICLE_ACCEPT_SALE: (VehicleLifecycle.LISTED, VehicleLifecycle.SALE_AGREED),
    RetailAction.VEHICLE_SETTLE_SALE: (VehicleLifecycle.SALE_AGREED, VehicleLifecycle.SOLD),
}

_NEXT_ACTION: dict[VehicleLifecycle, RetailAction] = {
    before: action for action, (before, _) in _ACTION_TRANSITIONS.items()
}


@dataclass(frozen=True)
class VehicleExportMission:
    tenant_id: str
    actor_id: str
    authority_chain: tuple[str, ...]
    purpose: str
    jurisdiction: str
    resource_id: str
    candidate_ref: str
    currency: str
    expected_net_profit_minor: int
    min_net_profit_minor: int
    autonomy_limit_minor: int
    authority_limit_minor: int
    risk_score: float
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True)
class VehicleStageRequest:
    action: RetailAction
    value_minor: int
    metadata: dict[str, Any]
    valid_until_ns: int
    idempotency_key: str
    evidence_refs: tuple[str, ...] = ()


def next_vehicle_action(status: str | VehicleLifecycle) -> RetailAction | None:
    lifecycle = status if isinstance(status, VehicleLifecycle) else VehicleLifecycle(status)
    return _NEXT_ACTION.get(lifecycle)


def expected_transition(action: RetailAction) -> tuple[VehicleLifecycle, VehicleLifecycle]:
    try:
        return _ACTION_TRANSITIONS[action]
    except KeyError as exc:
        raise ValueError(f"not a vehicle lifecycle action: {action.value}") from exc


def _common_metadata(mission: VehicleExportMission) -> dict[str, Any]:
    return {
        "candidate_ref": mission.candidate_ref,
        "expected_net_profit_minor": mission.expected_net_profit_minor,
        "min_net_profit_minor": mission.min_net_profit_minor,
        "autonomy_limit_minor": mission.autonomy_limit_minor,
        "authority_limit_minor": mission.authority_limit_minor,
    }


def build_vehicle_intent(
    mission: VehicleExportMission,
    request: VehicleStageRequest,
    *,
    before_state: dict[str, Any],
) -> RetailActionIntentV1:
    """Build the deterministic pack intent used for pre-submit admissibility.

    This function is pure. It cannot execute a provider. Real vehicle effects
    must be submitted as the corresponding registered Function through Operator.
    """
    required_before, after = expected_transition(request.action)
    actual_status = str(before_state.get("status", ""))
    if actual_status != required_before.value:
        raise ValueError(
            f"lifecycle mismatch for {request.action.value}: expected "
            f"{required_before.value}, got {actual_status or 'UNKNOWN'}"
        )
    version = before_state.get("version")
    if version is None:
        raise ValueError("vehicle lifecycle state missing version")

    metadata = {**_common_metadata(mission), **request.metadata}
    evidence_refs = tuple(dict.fromkeys((*mission.evidence_refs, *request.evidence_refs)))
    return RetailActionIntentV1(
        tenant_id=mission.tenant_id,
        action=request.action,
        actor_id=mission.actor_id,
        authority_chain=mission.authority_chain,
        purpose=mission.purpose,
        jurisdiction=mission.jurisdiction,
        resource_id=mission.resource_id,
        desired_change={"status": after.value},
        expected_before_state=dict(before_state),
        expected_version=str(version),
        value_minor=request.value_minor,
        currency=mission.currency,
        risk_score=mission.risk_score,
        valid_until_ns=request.valid_until_ns,
        idempotency_key=request.idempotency_key,
        evidence_refs=evidence_refs,
        metadata=metadata,
    )


def vehicle_trade_payload(
    mission: VehicleExportMission,
    request: VehicleStageRequest,
    *,
    before_state: dict[str, Any],
) -> dict[str, Any]:
    """Lower an admitted stage into the one typed Operator Function input."""
    intent = build_vehicle_intent(mission, request, before_state=before_state)
    return {
        "vehicle_ref": mission.resource_id,
        "candidate_ref": mission.candidate_ref,
        "value_minor": intent.value_minor,
        "currency": intent.currency,
        "expected_net_profit_minor": mission.expected_net_profit_minor,
        "min_net_profit_minor": mission.min_net_profit_minor,
        "autonomy_limit_minor": mission.autonomy_limit_minor,
        "authority_limit_minor": mission.authority_limit_minor,
        "evidence_refs": list(intent.evidence_refs),
        "expected_before_state": intent.expected_before_state,
        "expected_version": intent.expected_version,
        "desired_status": intent.desired_change["status"],
        **request.metadata,
    }
