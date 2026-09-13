"""Vendor-neutral production adapters.

Every difference between external vendors (auth headers, idempotency-header
names, payload shapes, state endpoints/fields, success states) is absorbed in a
VendorConfig — the Operator/REHT chain is identical regardless of vendor. Wiring
a real third-party endpoint (Stripe, Twilio, ServiceNow, ...) is a config
change, not a code change.
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any

from valo_workflow_isa.ports import (
    ExecutionResult,
    GatewayPort,
    Observation,
    VeritasPort,
)


@dataclass(frozen=True)
class VendorConfig:
    """Everything the transport needs to talk to ONE vendor's API."""

    name: str
    base_url: str
    send_path: str
    auth_header: tuple[str, str] | None = None
    idempotency_header: str | None = None
    id_field: str = "id"
    content_type: str = "json"
    body_builder: Any = None
    state_path: str = "/records/{id}"
    state_field: str = "status"
    success_state: str = "DELIVERED"
    effect_key: str = "delivered"


PAYMENTS_VENDOR = lambda base_url: VendorConfig(  # noqa: E731
    name="payments",
    base_url=base_url,
    send_path="/v1/payments",
    auth_header=("Authorization", "Bearer sk-test"),
    idempotency_header="Idempotency-Key",
    state_path="/v1/payments/{id}",
    state_field="status",
    success_state="SUCCEEDED",
    effect_key="payment_observed",
)

MESSAGING_VENDOR = lambda base_url: VendorConfig(  # noqa: E731
    name="messaging",
    base_url=base_url,
    send_path="/2010-04-01/Messages.json",
    auth_header=("Account-Sid", "AC-test"),
    idempotency_header="X-Idempotency-Key",
    state_path="/2010-04-01/Messages/{id}.json",
    state_field="status",
    success_state="delivered",
    effect_key="delivered",
)


class ConfiguredGateway(GatewayPort):
    """Transport-only. Builds the vendor request from config (auth + idempotency
    headers, path, payload), never decides anything."""

    def __init__(self, config: VendorConfig) -> None:
        self.config = config
        self.keys: set[str] = set()
        self.executions: list[dict[str, Any]] = []

    def execute(self, binding: str, action_contract: dict[str, Any], idempotency_key: str) -> ExecutionResult:
        if idempotency_key and idempotency_key in self.keys:
            return ExecutionResult(success=True, external_id="replayed", receipt_ref="receipt-replay")
        self.keys.add(idempotency_key)

        record_id = f"{idempotency_key or binding}-{len(self.executions)}"
        headers = {"Content-Type": "application/json"}
        if self.config.auth_header:
            headers[self.config.auth_header[0]] = self.config.auth_header[1]
        if self.config.idempotency_header and idempotency_key:
            headers[self.config.idempotency_header] = idempotency_key
        if self.config.body_builder is not None:
            body = self.config.body_builder(action_contract)
        else:
            body = {
                "id": record_id,
                "action_type": action_contract.get("action_type"),
                "binding": binding,
            }
        if self.config.content_type == "form":
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            payload = urllib.parse.urlencode(body).encode("utf-8")
        else:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{self.config.base_url}{self.config.send_path}",
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                body = json.loads(response.read().decode("utf-8") or "{}")
        except Exception as exc:
            return ExecutionResult(
                success=False, external_id=None, receipt_ref=None, payload={"error": str(exc)}
            )

        external_id = body.get(self.config.id_field) or body.get("id")
        self.executions.append(
            {"binding": binding, "action_type": action_contract.get("action_type"), "external_id": external_id}
        )
        return ExecutionResult(
            success=True,
            external_id=external_id,
            receipt_ref=f"receipt-{external_id}",
            payload={"external_record_id": external_id},
        )

    def has_effect(self, idempotency_key: str) -> bool:
        return idempotency_key in self.keys


class ConfiguredVeritas(VeritasPort):
    """Observation-only. Reads the vendor's state endpoint per config and maps
    the vendor's state field onto the effect key the postcondition expects."""

    def __init__(self, config: VendorConfig) -> None:
        self.config = config

    def observe(self, execution: ExecutionResult, action_contract: dict[str, Any]) -> Observation:
        external_id = execution.payload.get("external_record_id") or execution.external_id
        if not external_id:
            return self._unknown(execution)

        url = f"{self.config.base_url}{self.config.state_path.format(id=external_id)}"
        headers = {}
        if self.config.auth_header:
            headers[self.config.auth_header[0]] = self.config.auth_header[1]
        try:
            request = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(request, timeout=5) as response:
                record = json.loads(response.read().decode("utf-8") or "{}")
        except Exception:
            return self._unknown(execution)
        if not record or record.get(self.config.id_field, record.get("id")) is None:
            return self._unknown(execution)

        status = record.get(self.config.state_field)
        action_type = action_contract.get("action_type")
        success = status == self.config.success_state
        observed: dict[str, Any] = {"external_status": status}
        if action_type == "NOTIFY":
            observed[self.config.effect_key] = success
        elif action_type == "ISSUE_DECISION":
            observed["decision_issued"] = status is not None
        elif action_type in ("PAY", "RECONCILE_PAYMENT"):
            observed[self.config.effect_key] = success
        else:
            # Generic vendor operations must prove the configured success state;
            # merely receiving any state value is not evidence of the effect.
            observed[self.config.effect_key] = success
            observed["executed"] = success
        verified = any(value is True for key, value in observed.items() if key != "external_status")
        observed["outcome"] = "VERIFIED" if verified else "NOT_VERIFIED"
        return Observation(phase="EXECUTION_OBSERVED", observed=observed, receipt_ref=execution.receipt_ref)

    @staticmethod
    def _unknown(execution: ExecutionResult) -> Observation:
        return Observation(
            phase="EXECUTION_OBSERVED",
            observed={"outcome": "UNKNOWN", "verified": False},
            receipt_ref=execution.receipt_ref,
        )
