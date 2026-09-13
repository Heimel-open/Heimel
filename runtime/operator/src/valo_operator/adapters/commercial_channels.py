"""Provider-neutral commercial notification and payment configurations.

These helpers only construct VendorConfig objects. They do not send, authorize,
price, negotiate or charge anything. A configured edge becomes executable only
when a registered Function traverses the unchanged Operator -> Workflow ISA ->
VAIG/REHT/RACS -> Gateway -> Veritas/BARO chain.

The generic REST contract is intentionally small so a commissioned provider
adapter can translate it to email, SMS, voice or payment vendor specifics
without changing Operator semantics.
"""

from __future__ import annotations

import base64
import os
from typing import Any

from .vendor import VendorConfig

_NOTIFICATION_CHANNELS = {"email", "sms", "voice"}


def _auth_header(prefix: str) -> tuple[str, str] | None:
    """Build provider auth from environment without exposing credentials."""
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


def _notification_body(channel: str, prefix: str):
    def build(action_contract: dict[str, Any]) -> dict[str, Any]:
        params = action_contract.get("parameters") or {}
        notification = params.get("notification") or {}
        body: dict[str, Any] = {
            "channel": channel,
            "from": os.environ.get(f"{prefix}_FROM", ""),
            "to": notification.get("recipient", ""),
            "message": notification.get("message", ""),
        }
        if channel == "email":
            body["subject"] = notification.get("subject", "")
        return body

    return build


def notification_external_config(
    channel: str,
    base_url: str | None = None,
) -> VendorConfig:
    """Config for a commissioned notification edge: email, SMS or voice.

    Environment prefix is the upper-case channel, e.g. EMAIL_BASE_URL,
    SMS_AUTH, VOICE_FROM. Paths/state mappings can be changed per provider.
    """
    normalized = channel.strip().lower()
    if normalized not in _NOTIFICATION_CHANNELS:
        raise ValueError(f"unsupported notification channel: {channel}")
    prefix = normalized.upper()
    base = base_url or os.environ.get(f"{prefix}_BASE_URL", "")
    return VendorConfig(
        name=f"commercial-{normalized}",
        base_url=base,
        send_path=os.environ.get(
            f"{prefix}_SEND_PATH", f"/v1/{normalized}/messages"
        ),
        auth_header=_auth_header(prefix),
        idempotency_header=os.environ.get(
            f"{prefix}_IDEMPOTENCY_HEADER", "Idempotency-Key"
        ),
        id_field=os.environ.get(f"{prefix}_ID_FIELD", "id"),
        content_type=os.environ.get(f"{prefix}_CONTENT_TYPE", "json"),
        body_builder=_notification_body(normalized, prefix),
        state_path=os.environ.get(
            f"{prefix}_STATE_PATH", f"/v1/{normalized}/messages/{{id}}"
        ),
        state_field=os.environ.get(f"{prefix}_STATE_FIELD", "status"),
        success_state=os.environ.get(f"{prefix}_SUCCESS_STATE", "delivered"),
        effect_key="delivered",
    )


def _payment_body(action_contract: dict[str, Any]) -> dict[str, Any]:
    params = action_contract.get("parameters") or {}
    payment = params.get("payment") or params
    return {
        "customer_ref": payment.get("customer_ref", ""),
        "amount": payment.get("amount"),
        "currency": payment.get("currency", ""),
        "payment_method_ref": payment.get("payment_method_ref", ""),
        "description": payment.get("description", ""),
    }


def payment_external_config(base_url: str | None = None) -> VendorConfig:
    """Provider-neutral payment edge configuration.

    PAY_* configuration can point at Stripe, a bank-payment adapter, a smart-
    contract adapter, or another commissioned provider surface. The adapter is
    still transport only; REHT remains the final commit-time authority boundary.
    """
    base = base_url or os.environ.get("PAY_BASE_URL", "")
    return VendorConfig(
        name="commercial-payment",
        base_url=base,
        send_path=os.environ.get("PAY_SEND_PATH", "/v1/payments"),
        auth_header=_auth_header("PAY"),
        idempotency_header=os.environ.get(
            "PAY_IDEMPOTENCY_HEADER", "Idempotency-Key"
        ),
        id_field=os.environ.get("PAY_ID_FIELD", "id"),
        content_type=os.environ.get("PAY_CONTENT_TYPE", "json"),
        body_builder=_payment_body,
        state_path=os.environ.get("PAY_STATE_PATH", "/v1/payments/{id}"),
        state_field=os.environ.get("PAY_STATE_FIELD", "status"),
        success_state=os.environ.get("PAY_SUCCESS_STATE", "succeeded"),
        effect_key="payment_observed",
    )


def commercial_channel_configured(channel: str) -> bool:
    """Return whether minimal provider config exists; never tests authority."""
    normalized = channel.strip().lower()
    if normalized == "payment":
        prefix = "PAY"
        needs_from = False
    elif normalized in _NOTIFICATION_CHANNELS:
        prefix = normalized.upper()
        needs_from = True
    else:
        return False
    base = os.environ.get(f"{prefix}_BASE_URL")
    auth = _auth_header(prefix)
    from_value = os.environ.get(f"{prefix}_FROM") if needs_from else "not-required"
    return bool(base and auth and from_value)


__all__ = [
    "commercial_channel_configured",
    "notification_external_config",
    "payment_external_config",
]
