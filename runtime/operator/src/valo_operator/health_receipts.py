"""Minimum-disclosure health receipt projections and retention policy.

The projection is deliberately not a clinical record. It carries correlation,
digests and controlled references needed to reconstruct governance and effect
without copying raw audio, transcript or clinical note content into broadly
distributed operational receipts.
"""

from __future__ import annotations

import json
from enum import StrEnum
from hashlib import sha256
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _digest(value: str) -> str:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError("digest must be sha256:<64 hex chars>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError("digest must contain hexadecimal sha256 bytes") from exc
    return value.lower()


def _object_digest(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return f"sha256:{sha256(canonical.encode('utf-8')).hexdigest()}"


class HealthRetentionClass(StrEnum):
    RAW_AUDIO = "raw_audio"
    TRANSCRIPT = "transcript"
    CANDIDATE_RECORD = "candidate_record"
    COMMITTED_RECORD = "committed_record"
    OPERATIONAL_RECEIPT = "operational_receipt"
    MINIMUM_DISCLOSURE_PROOF = "minimum_disclosure_proof"


class HealthRetentionRule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    data_class: HealthRetentionClass
    retain: bool
    ttl_seconds: int | None = Field(default=None, ge=0)
    storage_policy_ref: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_rule(self) -> HealthRetentionRule:
        if not self.retain and self.ttl_seconds not in (None, 0):
            raise ValueError("non-retained data may only have zero or no TTL")
        return self


class HealthRetentionPolicyV1(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    policy_ref: str = Field(min_length=1)
    rules: tuple[HealthRetentionRule, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def require_unique_classes(self) -> HealthRetentionPolicyV1:
        classes = [rule.data_class for rule in self.rules]
        if len(classes) != len(set(classes)):
            raise ValueError("retention policy must define each data class at most once")
        return self


class HealthMinimumReceiptV1(BaseModel):
    """Operational receipt projection with no raw health content fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    correlation_id: str = Field(min_length=1)
    instance_id: str = Field(min_length=1)
    function_id: str = Field(min_length=1)
    effect: str = Field(min_length=1)
    decision: str = Field(min_length=1)
    permit_ref: str | None = None
    patient_context_digest: str
    candidate_or_action_digest: str
    destination_ref: str = Field(min_length=1)
    execution_receipt_ref: str | None = None
    observed_outcome_digest: str | None = None
    observed_outcome_status: str = Field(min_length=1)
    retention_policy_ref: str = Field(min_length=1)
    authority_effect: Literal["none"] = "none"

    _patient_digest = field_validator("patient_context_digest")(_digest)
    _candidate_digest = field_validator("candidate_or_action_digest")(_digest)

    @field_validator("observed_outcome_digest")
    @classmethod
    def validate_optional_outcome_digest(cls, value: str | None) -> str | None:
        return _digest(value) if value is not None else None

    @model_validator(mode="after")
    def require_effect_receipt_consistency(self) -> HealthMinimumReceiptV1:
        verified = self.observed_outcome_status.upper() == "VERIFIED"
        if verified and (self.execution_receipt_ref is None or self.observed_outcome_digest is None):
            raise ValueError("verified health outcome requires execution receipt and observed outcome digest")
        return self


HEALTH_FUNCTION_EFFECTS: dict[str, str] = {
    "valo.health.approve_note_draft": "review_recorded",
    "valo.health.commit_clinical_note": "clinical_record_committed",
    "valo.health.book_appointment": "appointment_booked",
    "valo.health.reschedule_appointment": "appointment_rescheduled",
    "valo.health.cancel_appointment": "appointment_cancelled",
    "valo.health.capture_renewal_request": "renewal_request_captured",
    "valo.health.route_renewal_request": "renewal_request_routed",
    "valo.health.request_clinical_review": "clinical_review_requested",
    "valo.health.record_clinician_decision": "clinician_decision_recorded",
    "valo.health.notify_patient": "patient_notified",
}

FORBIDDEN_HEALTH_RECEIPT_FIELDS = frozenset(
    {
        "raw_audio",
        "audio_bytes",
        "transcript",
        "transcript_text",
        "clinical_note",
        "note_text",
        "medication_name",
        "patient_name",
        "date_of_birth",
        "phone_number",
    }
)


def project_health_minimum_receipt(
    result: Any,
    *,
    patient_context_digest: str,
    candidate_or_action_digest: str,
    destination_ref: str,
    retention_policy_ref: str,
) -> HealthMinimumReceiptV1:
    """Project an Operator result to a minimum-disclosure health proof.

    Only canonical digests/refs from caller-controlled evidence are accepted.
    Raw request inputs or health content are never copied into the projection.
    """
    effect = HEALTH_FUNCTION_EFFECTS.get(result.function_id)
    if effect is None:
        raise ValueError(f"unsupported health Function for receipt projection: {result.function_id}")

    effect_receipt = next(
        (receipt for receipt in reversed(result.receipts) if receipt.get("kind") == "effect_verified"),
        None,
    )
    if result.effect_verified:
        status = "VERIFIED"
    elif result.decision == "DENY":
        status = "NOT_EXECUTED"
    else:
        status = "UNKNOWN"

    receipt = HealthMinimumReceiptV1(
        correlation_id=result.correlation_id,
        instance_id=result.instance_id or "unknown-instance",
        function_id=result.function_id,
        effect=effect,
        decision=result.decision or "NONE",
        permit_ref=result.permit,
        patient_context_digest=patient_context_digest,
        candidate_or_action_digest=candidate_or_action_digest,
        destination_ref=destination_ref,
        execution_receipt_ref=effect_receipt.get("receipt_ref") if effect_receipt else None,
        observed_outcome_digest=_object_digest(effect_receipt) if effect_receipt else None,
        observed_outcome_status=status,
        retention_policy_ref=retention_policy_ref,
    )
    assert_minimum_disclosure(receipt)
    return receipt


def assert_minimum_disclosure(receipt: HealthMinimumReceiptV1) -> None:
    present = set(receipt.model_dump())
    leaked = present & FORBIDDEN_HEALTH_RECEIPT_FIELDS
    if leaked:
        raise ValueError(f"health minimum receipt exposes prohibited fields: {sorted(leaked)}")
