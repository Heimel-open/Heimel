from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class RetailAction(str, Enum):
    MOVE_INVENTORY = "RETAIL_MOVE_INVENTORY"
    SET_PRICE = "RETAIL_SET_PRICE"
    CREATE_PROMOTION = "RETAIL_CREATE_PROMOTION"
    CREATE_PURCHASE_ORDER = "RETAIL_CREATE_PURCHASE_ORDER"
    REFUND_ORDER = "RETAIL_REFUND_ORDER"
    VEHICLE_PURCHASE = "RETAIL_VEHICLE_PURCHASE"
    VEHICLE_BOOK_TRANSPORT = "RETAIL_VEHICLE_BOOK_TRANSPORT"
    VEHICLE_EXPORT = "RETAIL_VEHICLE_EXPORT"
    VEHICLE_LIST_SALE = "RETAIL_VEHICLE_LIST_SALE"
    VEHICLE_ACCEPT_SALE = "RETAIL_VEHICLE_ACCEPT_SALE"
    VEHICLE_SETTLE_SALE = "RETAIL_VEHICLE_SETTLE_SALE"


class Decision(str, Enum):
    ALLOW = "ALLOW"
    MODIFY = "MODIFY"
    DEFER = "DEFER"
    DENY = "DENY"
    STEP_UP = "STEP_UP"
    HALT = "HALT"


@dataclass(frozen=True)
class RetailActionIntentV1:
    tenant_id: str
    action: RetailAction
    actor_id: str
    authority_chain: tuple[str, ...]
    purpose: str
    jurisdiction: str
    resource_id: str
    desired_change: dict[str, Any]
    expected_before_state: dict[str, Any]
    expected_version: str
    value_minor: int
    currency: str
    risk_score: float
    valid_until_ns: int
    idempotency_key: str
    evidence_refs: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetailExecutionReceiptV1:
    tenant_id: str
    idempotency_key: str
    proposed_action: dict[str, Any]
    authorized_action: dict[str, Any]
    provider_request: dict[str, Any] | None
    before_state: dict[str, Any]
    after_state: dict[str, Any] | None
    result: str
    error: str | None
    provider_response_hash: str | None
    decision: Decision
    authority_chain: tuple[str, ...]
    reversal_ref: str | None
    veritas_receipt_ref: str
