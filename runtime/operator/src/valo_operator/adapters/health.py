# ruff: noqa: I001
"""Provider-neutral health-system transport configuration.

The adapters map already-governed health actions to scheduling, EHR and renewal
work-queue protocols and independently read destination state back. They never
choose a health action, identity, clinical decision, authority or REHT outcome.
"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import replace
from typing import Any

from valo_workflow_isa.ports import ExecutionResult, Observation, VeritasPort

from .vendor import ConfiguredGateway, VendorConfig

HEALTH_ACTION_EFFECTS: dict[str, str] = {
    "APPROVE_NOTE_DRAFT": "review_recorded",
    "COMMIT_CLINICAL_NOTE": "clinical_record_committed",
    "BOOK_APPOINTMENT": "appointment_booked",
    "RESCHEDULE_APPOINTMENT": "appointment_rescheduled",
    "CANCEL_APPOINTMENT": "appointment_cancelled",
    "CAPTURE_RENEWAL_REQUEST": "renewal_request_captured",
    "ROUTE_RENEWAL_REQUEST": "renewal_request_routed",
    "REQUEST_CLINICAL_REVIEW": "clinical_review_requested",
    "RECORD_CLINICIAN_DECISION": "clinician_decision_recorded",
    "NOTIFY_PATIENT": "patient_notified",
}


def scheduling_vendor(
    base_url: str,
    *,
    name: str = "scheduling",
    auth_header: tuple[str, str] | None = None,
    send_path: str = "/appointments/actions",
    state_path: str = "/appointments/actions/{id}",
    id_field: str = "id",
    state_field: str = "status",
    success_state: str = "APPLIED",
    idempotency_header: str = "Idempotency-Key",
) -> VendorConfig:
    return VendorConfig(
        name=name,
        base_url=base_url,
        send_path=send_path,
        auth_header=auth_header,
        idempotency_header=idempotency_header,
        id_field=id_field,
        state_path=state_path,
        state_field=state_field,
        success_state=success_state,
        effect_key="appointment_changed",
        body_builder=_health_body,
    )


def ehr_vendor(
    base_url: str,
    *,
    name: str = "ehr",
    auth_header: tuple[str, str] | None = None,
    send_path: str = "/clinical-notes",
    state_path: str = "/clinical-notes/{id}",
    id_field: str = "id",
    state_field: str = "status",
    success_state: str = "COMMITTED",
    idempotency_header: str = "Idempotency-Key",
) -> VendorConfig:
    return VendorConfig(
        name=name,
        base_url=base_url,
        send_path=send_path,
        auth_header=auth_header,
        idempotency_header=idempotency_header,
        id_field=id_field,
        state_path=state_path,
        state_field=state_field,
        success_state=success_state,
        effect_key="clinical_record_committed",
        body_builder=_health_body,
    )


def renewal_workqueue_vendor(
    base_url: str,
    *,
    name: str = "renewal-workqueue",
    auth_header: tuple[str, str] | None = None,
    send_path: str = "/renewals/actions",
    state_path: str = "/renewals/actions/{id}",
    id_field: str = "id",
    state_field: str = "status",
    success_state: str = "APPLIED",
    idempotency_header: str = "Idempotency-Key",
) -> VendorConfig:
    return VendorConfig(
        name=name,
        base_url=base_url,
        send_path=send_path,
        auth_header=auth_header,
        idempotency_header=idempotency_header,
        id_field=id_field,
        state_path=state_path,
        state_field=state_field,
        success_state=success_state,
        effect_key="renewal_workflow_changed",
        body_builder=_health_body,
    )


def provider_variant(
    config: VendorConfig,
    *,
    name: str,
    send_path: str,
    state_path: str,
    id_field: str,
    state_field: str,
    success_state: str,
    idempotency_header: str,
    auth_header: tuple[str, str] | None = None,
) -> VendorConfig:
    """Create another provider protocol without changing governance semantics."""
    return replace(
        config,
        name=name,
        send_path=send_path,
        state_path=state_path,
        id_field=id_field,
        state_field=state_field,
        success_state=success_state,
        idempotency_header=idempotency_header,
        auth_header=auth_header,
    )


def _health_body(action_contract: dict[str, Any]) -> dict[str, Any]:
    """Minimum transport body. Authority/permit material is deliberately absent."""
    body = {
        "action_type": action_contract.get("action_type"),
        "target": action_contract.get("target"),
        "requested_transition": action_contract.get("requested_transition"),
        "postconditions": action_contract.get("postconditions"),
    }
    parameters = action_contract.get("parameters") or {}
    candidates: list[dict[str, Any]] = [action_contract]
    if isinstance(parameters, dict):
        candidates.extend(value for value in parameters.values() if isinstance(value, dict))
    for key in (
        "patient_ref",
        "candidate_ref",
        "candidate_digest",
        "content_digest",
        "action_ref",
        "payload_digest",
        "renewal_ref",
        "appointment_ref",
        "slot_ref",
        "message_ref",
        "recipient_ref",
    ):
        for candidate in candidates:
            if key in candidate:
                body[key] = candidate[key]
                break
    return body


class HealthConfiguredGateway(ConfiguredGateway):
    """Alias with an explicit health boundary: still transport-only."""


class HealthConfiguredVeritas(VeritasPort):
    """Read back exact provider state and map it to the health Function effect."""

    def __init__(self, config: VendorConfig) -> None:
        self.config = config

    def observe(self, execution: ExecutionResult, action_contract: dict[str, Any]) -> Observation:
        external_id = execution.payload.get("external_record_id") or execution.external_id
        if not external_id or external_id == "replayed":
            return self._unknown(execution)

        url = f"{self.config.base_url}{self.config.state_path.format(id=external_id)}"
        headers: dict[str, str] = {}
        if self.config.auth_header:
            headers[self.config.auth_header[0]] = self.config.auth_header[1]
        try:
            request = urllib.request.Request(url, headers=headers, method="GET")
            with urllib.request.urlopen(request, timeout=5) as response:
                record = json.loads(response.read().decode("utf-8") or "{}")
        except Exception:
            return self._unknown(execution)

        observed_id = record.get(self.config.id_field, record.get("id"))
        if observed_id is None or str(observed_id) != str(external_id):
            return self._unknown(execution)

        action_type = str(action_contract.get("action_type") or "")
        effect_key = HEALTH_ACTION_EFFECTS.get(action_type)
        if effect_key is None:
            return Observation(
                phase="EXECUTION_OBSERVED",
                observed={
                    "outcome": "NOT_VERIFIED",
                    "verified": False,
                    "reason": "unknown_health_action_type",
                },
                receipt_ref=execution.receipt_ref,
            )

        status = record.get(self.config.state_field)
        success = status == self.config.success_state
        observed = {
            "external_status": status,
            effect_key: success,
            "outcome": "VERIFIED" if success else "NOT_VERIFIED",
            "verified": success,
        }
        return Observation(
            phase="EXECUTION_OBSERVED",
            observed=observed,
            receipt_ref=execution.receipt_ref,
        )

    @staticmethod
    def _unknown(execution: ExecutionResult) -> Observation:
        return Observation(
            phase="EXECUTION_OBSERVED",
            observed={"outcome": "UNKNOWN", "verified": False},
            receipt_ref=execution.receipt_ref,
        )
