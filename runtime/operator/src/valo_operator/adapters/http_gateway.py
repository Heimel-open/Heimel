"""Production Gateway adapter: executes the action against a REAL external
system over HTTP, with idempotency keys and receipts."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from valo_workflow_isa.ports import ExecutionResult, GatewayPort


class HttpGateway(GatewayPort):
    """Executes against an external HTTP endpoint. Idempotency is enforced both
    locally (replayed keys never re-send) and by the external system (same id
    returns the same record)."""

    def __init__(self, base_url: str, endpoint: str = "/") -> None:
        self.base_url = base_url.rstrip("/")
        self.endpoint = endpoint
        self.keys: set[str] = set()
        self.executions: list[dict[str, Any]] = []

    def execute(self, binding: str, action_contract: dict[str, Any], idempotency_key: str) -> ExecutionResult:
        if idempotency_key and idempotency_key in self.keys:
            return ExecutionResult(success=True, external_id="replayed", receipt_ref="receipt-replay")
        self.keys.add(idempotency_key)

        record_id = f"{idempotency_key or binding}-{len(self.executions)}"
        payload = json.dumps({
            "id": record_id,
            "action_type": action_contract.get("action_type"),
            "binding": binding,
        }).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}{self.endpoint}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=5) as response:
                body = json.loads(response.read().decode("utf-8") or "{}")
        except Exception as exc:  # network failure -> execution did NOT happen
            return ExecutionResult(
                success=False, external_id=None, receipt_ref=None, payload={"error": str(exc)}
            )

        self.executions.append(
            {"binding": binding, "action_type": action_contract.get("action_type"), "external_id": body.get("id")}
        )
        return ExecutionResult(
            success=True,
            external_id=body.get("id"),
            receipt_ref=f"receipt-{body.get('id')}",
            payload={"external_record_id": body.get("id")},
        )

    def has_effect(self, idempotency_key: str) -> bool:
        return idempotency_key in self.keys
