"""External Production Proof harness (messaging first).

The internal messaging fixture and the REAL messaging vendor differ ONLY in a
VendorConfig (base_url, endpoint/path, auth/header construction, content_type,
body_builder, observation/status mapping). REHT, Operator, Function Fabric,
Workflow ISA and Kernel are unchanged.

Twilio specifics are absorbed here, never in the chain: classic Messages
endpoint uses HTTP Basic auth, an account-specific path and
application/x-www-form-urlencoded. Auth is built from API key + secret or a
pre-computed header value. Credentials come from env only and are never
logged.

Env: MSG_BASE_URL, MSG_FROM, and either MSG_AUTH (full Authorization header
value) or MSG_AUTH_USER + MSG_AUTH_SECRET (Twilio API key + secret).
"""

from __future__ import annotations

import base64
import os
from typing import Any

from .vendor import VendorConfig


def _messaging_body(action_contract: dict[str, Any]) -> dict[str, Any]:
    """Map the NOTIFY action contract onto the vendor's message payload. Pure
    data mapping; recipient/body come from the action's parameters."""
    params = action_contract.get("parameters") or {}
    notification = params.get("notification") or {}
    return {
        "From": os.environ.get("MSG_FROM", ""),
        "To": notification.get("recipient", ""),
        "Body": notification.get("message", ""),
    }


def _auth_header() -> tuple[str, str] | None:
    auth = os.environ.get("MSG_AUTH")
    if auth:
        return ("Authorization", auth)
    user = os.environ.get("MSG_AUTH_USER")
    secret = os.environ.get("MSG_AUTH_SECRET")
    if user and secret:
        token = base64.b64encode(f"{user}:{secret}".encode()).decode("ascii")
        return ("Authorization", f"Basic {token}")
    return None


def messaging_external_config(base_url: str | None = None) -> VendorConfig:
    """A REAL messaging vendor config driven by environment variables.

    MSG_BASE_URL should include the account-specific path for the classic
    endpoint (e.g. https://api.twilio.com/2010-04-01/Accounts/ACxxxx). When
    unset, the config points at the internal messaging fixture so the harness
    mechanics run locally; setting the env vars makes the swap config-only.
    """
    base = base_url or os.environ.get("MSG_BASE_URL", "")
    auth = _auth_header()
    return VendorConfig(
        name="messaging-external",
        base_url=base,
        send_path="/Messages.json" if base else "/2010-04-01/Messages.json",
        auth_header=auth,
        idempotency_header="X-Idempotency-Key",
        id_field="sid" if base else "id",
        content_type="form" if base else "json",
        body_builder=_messaging_body,
        state_path="/Messages/{id}.json" if base else "/2010-04-01/Messages/{id}.json",
        state_field="status",
        success_state="delivered",
        effect_key="delivered",
    )


def external_proof_configured() -> bool:
    """True when the real external messaging endpoint is configured (env set)."""
    base = os.environ.get("MSG_BASE_URL")
    from_ = os.environ.get("MSG_FROM")
    auth = os.environ.get("MSG_AUTH") or (
        os.environ.get("MSG_AUTH_USER") and os.environ.get("MSG_AUTH_SECRET")
    )
    return bool(base and from_ and auth)
