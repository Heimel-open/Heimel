"""Production Veritas adapter: OBSERVES reality at the external system after
the Gateway executed. The send response is never trusted — the observed state
endpoint is what proves (or disproves) the effect. A timeout or a missing
record yields outcome=UNKNOWN, never a synthetic success."""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from valo_workflow_isa.ports import ExecutionResult, Observation, VeritasPort


class HttpVeritas(VeritasPort):
    """Queries the external system's state endpoint to observe what actually
    happened. HTTP 200 from the send does NOT mean delivered."""

    def __init__(self, base_url: str, records_endpoint: str = "/records/") -> None:
        self.base_url = base_url.rstrip("/")
        self.records_endpoint = records_endpoint

    def observe(self, execution: ExecutionResult, action_contract: dict[str, Any]) -> Observation:
        external_id = execution.payload.get("external_record_id") or execution.external_id
        if not external_id:
            return self._unknown(execution)

        url = f"{self.base_url}{self.records_endpoint}{external_id}"
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                record = json.loads(response.read().decode("utf-8") or "{}")
        except Exception:
            return self._unknown(execution)
        if not record or record.get("id") is None:
            return self._unknown(execution)

        status = record.get("status")
        action_type = action_contract.get("action_type")
        observed: dict[str, Any] = {"external_status": status}
        if action_type == "NOTIFY":
            observed["delivered"] = status == "DELIVERED"
        elif action_type == "ISSUE_DECISION":
            observed["decision_issued"] = status == "DELIVERED"
        elif action_type in ("PAY", "RECONCILE_PAYMENT"):
            observed["payment_observed"] = status == "COMMITTED"
        else:
            observed["executed"] = status is not None
        observed["outcome"] = "VERIFIED" if _verified(observed) else "NOT_VERIFIED"
        return Observation(phase="EXECUTION_OBSERVED", observed=observed, receipt_ref=execution.receipt_ref)

    @staticmethod
    def _unknown(execution: ExecutionResult) -> Observation:
        return Observation(
            phase="EXECUTION_OBSERVED",
            observed={"outcome": "UNKNOWN", "verified": False},
            receipt_ref=execution.receipt_ref,
        )


def _verified(observed: dict[str, Any]) -> bool:
    return any(
        observed.get(key) is True
        for key in ("delivered", "decision_issued", "payment_observed", "executed")
    )
