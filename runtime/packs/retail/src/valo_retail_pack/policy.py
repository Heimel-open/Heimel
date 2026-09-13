from __future__ import annotations

from dataclasses import dataclass

from .contracts import Decision, RetailAction, RetailActionIntentV1


@dataclass(frozen=True)
class PolicyResult:
    decision: Decision
    reason: str


_VEHICLE_ACTIONS = {
    RetailAction.VEHICLE_PURCHASE,
    RetailAction.VEHICLE_BOOK_TRANSPORT,
    RetailAction.VEHICLE_EXPORT,
    RetailAction.VEHICLE_LIST_SALE,
    RetailAction.VEHICLE_ACCEPT_SALE,
    RetailAction.VEHICLE_SETTLE_SALE,
}


def _missing(metadata: dict, required: tuple[str, ...]) -> bool:
    return any(key not in metadata for key in required)


def _vehicle_limits(intent: RetailActionIntentV1) -> PolicyResult | None:
    metadata = intent.metadata
    required = (
        "autonomy_limit_minor",
        "authority_limit_minor",
        "candidate_ref",
        "expected_net_profit_minor",
        "min_net_profit_minor",
    )
    if _missing(metadata, required):
        return PolicyResult(Decision.DENY, "vehicle authority/economics evidence incomplete")
    if metadata["expected_net_profit_minor"] < metadata["min_net_profit_minor"]:
        return PolicyResult(Decision.DENY, "expected net profit below mandate")
    if intent.value_minor > metadata["authority_limit_minor"]:
        return PolicyResult(Decision.STEP_UP, "vehicle authority limit exceeded")
    if intent.value_minor > metadata["autonomy_limit_minor"]:
        return PolicyResult(Decision.STEP_UP, "vehicle autonomy limit exceeded")
    return None


def evaluate_retail_intent(
    intent: RetailActionIntentV1,
    *,
    now_ns: int,
    high_value_minor: int = 100_000,
) -> PolicyResult:
    if not intent.tenant_id or not intent.actor_id:
        return PolicyResult(Decision.DENY, "missing tenant or actor")
    if not intent.authority_chain:
        return PolicyResult(Decision.DENY, "missing authority")
    if not intent.evidence_refs:
        return PolicyResult(Decision.DENY, "missing evidence")
    if intent.valid_until_ns <= now_ns:
        return PolicyResult(Decision.DENY, "intent expired")

    metadata = intent.metadata

    if intent.action in _VEHICLE_ACTIONS:
        limit_result = _vehicle_limits(intent)
        if limit_result is not None:
            return limit_result
    elif intent.value_minor >= high_value_minor:
        return PolicyResult(Decision.STEP_UP, "high value")

    if intent.action is RetailAction.MOVE_INVENTORY:
        required = ("available", "reserved", "safety_stock", "requested_qty")
        if _missing(metadata, required):
            return PolicyResult(Decision.DENY, "inventory evidence incomplete")
        if metadata["available"] - metadata["reserved"] - metadata["requested_qty"] < metadata["safety_stock"]:
            return PolicyResult(Decision.DENY, "safety stock breach")

    elif intent.action is RetailAction.SET_PRICE:
        required = ("margin_after", "min_margin", "change_pct", "max_change_pct", "reference_price_30d")
        if _missing(metadata, required):
            return PolicyResult(Decision.DENY, "price evidence incomplete")
        if metadata["margin_after"] < metadata["min_margin"] or abs(metadata["change_pct"]) > metadata["max_change_pct"]:
            return PolicyResult(Decision.DENY, "price boundary breach")

    elif intent.action is RetailAction.CREATE_PROMOTION:
        required = ("budget_minor", "audience", "start_ns", "end_ns", "stacking_allowed")
        if _missing(metadata, required):
            return PolicyResult(Decision.DENY, "promotion evidence incomplete")

    elif intent.action is RetailAction.CREATE_PURCHASE_ORDER:
        required = ("supplier_id", "contract_ref", "budget_ref", "authority_limit_minor")
        if _missing(metadata, required):
            return PolicyResult(Decision.DENY, "purchase evidence incomplete")
        if intent.value_minor > metadata["authority_limit_minor"]:
            return PolicyResult(Decision.STEP_UP, "purchase authority exceeded")
        if intent.desired_change.get("status") != "ON_HOLD":
            return PolicyResult(Decision.MODIFY, "purchase orders must start ON_HOLD")

    elif intent.action is RetailAction.REFUND_ORDER:
        required = ("order_id", "payment_ref", "return_status", "reason", "fraud_indicator", "restocking")
        if _missing(metadata, required):
            return PolicyResult(Decision.DENY, "refund evidence incomplete")
        if metadata["fraud_indicator"]:
            return PolicyResult(Decision.STEP_UP, "fraud indicator")

    elif intent.action is RetailAction.VEHICLE_PURCHASE:
        required = (
            "seller_id",
            "purchase_price_minor",
            "market_evidence_fresh",
            "refund_evidence_ref",
            "foreign_value_evidence_ref",
        )
        if _missing(metadata, required):
            return PolicyResult(Decision.DENY, "vehicle purchase evidence incomplete")
        if not metadata["market_evidence_fresh"]:
            return PolicyResult(Decision.DEFER, "vehicle economics evidence stale")
        if int(metadata["purchase_price_minor"]) != intent.value_minor:
            return PolicyResult(Decision.DENY, "purchase value binding mismatch")
        if intent.desired_change.get("status") != "PURCHASED":
            return PolicyResult(Decision.DENY, "purchase must transition to PURCHASED")

    elif intent.action is RetailAction.VEHICLE_BOOK_TRANSPORT:
        required = ("carrier_id", "quote_ref", "insured", "pickup_window", "delivery_destination")
        if _missing(metadata, required):
            return PolicyResult(Decision.DENY, "vehicle transport evidence incomplete")
        if not metadata["insured"]:
            return PolicyResult(Decision.DENY, "vehicle transport must be insured")
        if intent.desired_change.get("status") != "IN_TRANSIT":
            return PolicyResult(Decision.DENY, "transport must transition to IN_TRANSIT")

    elif intent.action is RetailAction.VEHICLE_EXPORT:
        required = (
            "export_destination",
            "declaration_ref",
            "vehicle_export_eligible",
            "waste_classification",
        )
        if _missing(metadata, required):
            return PolicyResult(Decision.DENY, "vehicle export evidence incomplete")
        if not metadata["vehicle_export_eligible"]:
            return PolicyResult(Decision.DENY, "vehicle not export-refund eligible")
        if metadata["waste_classification"] != "NOT_WASTE":
            return PolicyResult(Decision.DENY, "vehicle classified as waste")
        if intent.desired_change.get("status") != "EXPORTED":
            return PolicyResult(Decision.DENY, "export must transition to EXPORTED")

    elif intent.action is RetailAction.VEHICLE_LIST_SALE:
        required = ("marketplace_id", "listing_price_minor", "floor_price_minor", "foreign_market_value_minor")
        if _missing(metadata, required):
            return PolicyResult(Decision.DENY, "vehicle listing evidence incomplete")
        if metadata["listing_price_minor"] < metadata["floor_price_minor"]:
            return PolicyResult(Decision.DENY, "listing price below floor")
        if intent.desired_change.get("status") != "LISTED":
            return PolicyResult(Decision.DENY, "listing must transition to LISTED")

    elif intent.action is RetailAction.VEHICLE_ACCEPT_SALE:
        required = ("buyer_id", "buyer_verified", "offer_minor", "floor_price_minor", "payment_method_ref")
        if _missing(metadata, required):
            return PolicyResult(Decision.DENY, "vehicle sale evidence incomplete")
        if not metadata["buyer_verified"]:
            return PolicyResult(Decision.DENY, "buyer not verified")
        if metadata["offer_minor"] < metadata["floor_price_minor"]:
            return PolicyResult(Decision.DENY, "sale offer below floor")
        if int(metadata["offer_minor"]) != intent.value_minor:
            return PolicyResult(Decision.DENY, "sale value binding mismatch")
        if intent.desired_change.get("status") != "SALE_AGREED":
            return PolicyResult(Decision.DENY, "sale acceptance must transition to SALE_AGREED")

    elif intent.action is RetailAction.VEHICLE_SETTLE_SALE:
        required = ("payment_ref", "payment_verified", "title_transfer_ref", "title_transfer_verified")
        if _missing(metadata, required):
            return PolicyResult(Decision.DENY, "vehicle settlement evidence incomplete")
        if not metadata["payment_verified"] or not metadata["title_transfer_verified"]:
            return PolicyResult(Decision.DEFER, "vehicle settlement not independently verified")
        if intent.desired_change.get("status") != "SOLD":
            return PolicyResult(Decision.DENY, "settlement must transition to SOLD")

    return PolicyResult(Decision.ALLOW, "admissible")
