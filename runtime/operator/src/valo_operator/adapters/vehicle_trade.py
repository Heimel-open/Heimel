"""Provider-neutral external edges for the governed vehicle export loop.

These helpers only build VendorConfig objects. They never select a vehicle,
set economic policy, negotiate outside a registered Function, or create
execution authority. The same Operator -> REHT -> Gateway -> Veritas chain is
used for purchase, transport, export/declaration and foreign sale.
"""

from __future__ import annotations

import base64
import os
from typing import Any, Callable

from .vendor import VendorConfig

_VEHICLE_OPERATIONS = {"purchase", "transport", "export", "sale"}


def _prefix(operation: str) -> str:
    normalized = operation.strip().lower()
    if normalized not in _VEHICLE_OPERATIONS:
        raise ValueError(f"unsupported vehicle operation: {operation}")
    return f"VEHICLE_{normalized.upper()}"


def _auth_header(prefix: str) -> tuple[str, str] | None:
    header_name = os.environ.get(f"{prefix}_AUTH_HEADER", "Authorization")
    auth = os.environ.get(f"{prefix}_AUTH")
    if auth:
        return (header_name, auth)
    user = os.environ.get(f"{prefix}_AUTH_USER")
    secret = os.environ.get(f"{prefix}_AUTH_SECRET")
    if user and secret:
        token = base64.b64encode(f"{user}:{secret}".encode()).decode("ascii")
        return (header_name, f"Basic {token}")
    return None


def _params(action_contract: dict[str, Any]) -> dict[str, Any]:
    parameters = action_contract.get("parameters") or {}
    vehicle = parameters.get("vehicle_trade") or parameters
    return vehicle if isinstance(vehicle, dict) else {}


def _purchase_body(action_contract: dict[str, Any]) -> dict[str, Any]:
    p = _params(action_contract)
    return {
        "vehicle_ref": p.get("vehicle_ref", ""),
        "seller_ref": p.get("seller_ref", ""),
        "listing_ref": p.get("listing_ref", ""),
        "amount_minor": p.get("amount_minor"),
        "currency": p.get("currency", ""),
        "payment_method_ref": p.get("payment_method_ref", ""),
    }


def _transport_body(action_contract: dict[str, Any]) -> dict[str, Any]:
    p = _params(action_contract)
    return {
        "vehicle_ref": p.get("vehicle_ref", ""),
        "carrier_ref": p.get("carrier_ref", ""),
        "quote_ref": p.get("quote_ref", ""),
        "pickup": p.get("pickup", ""),
        "destination": p.get("destination", ""),
        "insured": bool(p.get("insured", False)),
    }


def _export_body(action_contract: dict[str, Any]) -> dict[str, Any]:
    p = _params(action_contract)
    return {
        "vehicle_ref": p.get("vehicle_ref", ""),
        "destination": p.get("destination", ""),
        "declaration_ref": p.get("declaration_ref", ""),
        "refund_evidence_ref": p.get("refund_evidence_ref", ""),
        "waste_classification": p.get("waste_classification", ""),
    }


def _sale_body(action_contract: dict[str, Any]) -> dict[str, Any]:
    p = _params(action_contract)
    return {
        "vehicle_ref": p.get("vehicle_ref", ""),
        "listing_ref": p.get("listing_ref", ""),
        "buyer_ref": p.get("buyer_ref", ""),
        "amount_minor": p.get("amount_minor"),
        "currency": p.get("currency", ""),
        "payment_method_ref": p.get("payment_method_ref", ""),
        "title_transfer_ref": p.get("title_transfer_ref", ""),
    }


_BODY_BUILDERS: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {
    "purchase": _purchase_body,
    "transport": _transport_body,
    "export": _export_body,
    "sale": _sale_body,
}

_DEFAULT_PATHS = {
    "purchase": "/v1/vehicle/purchases",
    "transport": "/v1/vehicle/transports",
    "export": "/v1/vehicle/exports",
    "sale": "/v1/vehicle/sales",
}

_DEFAULT_SUCCESS = {
    "purchase": "purchased",
    "transport": "booked",
    "export": "exported",
    "sale": "sold",
}


def vehicle_trade_external_config(
    operation: str,
    base_url: str | None = None,
) -> VendorConfig:
    """Build one commissioned vehicle-trade provider edge from environment."""
    normalized = operation.strip().lower()
    prefix = _prefix(normalized)
    base = base_url or os.environ.get(f"{prefix}_BASE_URL", "")
    default_path = _DEFAULT_PATHS[normalized]
    return VendorConfig(
        name=f"vehicle-{normalized}",
        base_url=base,
        send_path=os.environ.get(f"{prefix}_SEND_PATH", default_path),
        auth_header=_auth_header(prefix),
        idempotency_header=os.environ.get(
            f"{prefix}_IDEMPOTENCY_HEADER", "Idempotency-Key"
        ),
        id_field=os.environ.get(f"{prefix}_ID_FIELD", "id"),
        content_type=os.environ.get(f"{prefix}_CONTENT_TYPE", "json"),
        body_builder=_BODY_BUILDERS[normalized],
        state_path=os.environ.get(f"{prefix}_STATE_PATH", f"{default_path}/{{id}}"),
        state_field=os.environ.get(f"{prefix}_STATE_FIELD", "status"),
        success_state=os.environ.get(
            f"{prefix}_SUCCESS_STATE", _DEFAULT_SUCCESS[normalized]
        ),
        effect_key=f"vehicle_{normalized}_verified",
    )


def vehicle_trade_edge_configured(operation: str) -> bool:
    """Check minimal transport configuration only; this is not authorization."""
    prefix = _prefix(operation)
    return bool(os.environ.get(f"{prefix}_BASE_URL") and _auth_header(prefix))


__all__ = [
    "vehicle_trade_edge_configured",
    "vehicle_trade_external_config",
]
