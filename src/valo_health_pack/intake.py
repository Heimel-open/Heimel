"""Provider-neutral health intake evidence and bounded work proposals.

This module deliberately stops before Operator and REHT. A voice/text intent is
evidence about requested work, not authority to perform it. Only resolved,
explicitly mapped intents may become a work proposal; informational and
ambiguous inputs emit no consequential proposal.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class HealthIntakeModality(StrEnum):
    TEXT = "text"
    VOICE = "voice"


class HealthIntentStatus(StrEnum):
    RESOLVED = "resolved"
    AMBIGUOUS = "ambiguous"
    UNSUPPORTED = "unsupported"


class HealthIntentKind(StrEnum):
    CREATE_NOTE_DRAFT = "create_note_draft"
    LOOKUP_APPOINTMENT = "lookup_appointment"
    BOOK_APPOINTMENT = "book_appointment"
    RESCHEDULE_APPOINTMENT = "reschedule_appointment"
    CANCEL_APPOINTMENT = "cancel_appointment"
    RENEWAL_REQUEST = "renewal_request"
    GENERAL_QUESTION = "general_question"
    UNKNOWN = "unknown"


def _validate_digest(value: str) -> str:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError("digest must be sha256:<64 hex chars>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError("digest must contain hexadecimal sha256 bytes") from exc
    return value.lower()


class HealthIntakeEvidenceV1(BaseModel):
    """Evidence that a health-related interaction was interpreted a certain way."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    intake_ref: str = Field(min_length=1)
    conversation_ref: str = Field(min_length=1)
    modality: HealthIntakeModality
    channel: str = Field(min_length=1)
    source_artifact_refs: tuple[str, ...] = Field(default_factory=tuple)
    transcript_digest: str | None = None
    text_digest: str | None = None
    intent: HealthIntentKind
    intent_status: HealthIntentStatus
    intent_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    intent_method_ref: str = Field(min_length=1)
    extracted_fields: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    observed_at: datetime
    expires_at: datetime
    authority_effect: Literal["none"] = "none"

    @field_validator("transcript_digest", "text_digest")
    @classmethod
    def validate_optional_digest(cls, value: str | None) -> str | None:
        return _validate_digest(value) if value is not None else None

    @model_validator(mode="after")
    def validate_source_and_window(self) -> HealthIntakeEvidenceV1:
        if self.expires_at <= self.observed_at:
            raise ValueError("expires_at must be after observed_at")
        if self.modality is HealthIntakeModality.VOICE:
            if self.transcript_digest is None or not self.source_artifact_refs:
                raise ValueError("voice intake requires transcript digest and source artifact reference")
        elif self.text_digest is None:
            raise ValueError("text intake requires text_digest")
        if self.intent_status is HealthIntentStatus.RESOLVED and self.intent is HealthIntentKind.UNKNOWN:
            raise ValueError("UNKNOWN intent cannot be marked resolved")
        return self


class HealthWorkProposalV1(BaseModel):
    """Non-authoritative proposal to invoke one already registered Function."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    correlation_id: str = Field(min_length=1)
    source_intake_ref: str = Field(min_length=1)
    function_id: str = Field(min_length=1)
    function_version: str = "1.0.0"
    input_name: str = Field(min_length=1)
    inputs: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    requires_fresh_reht: Literal[True] = True
    authority_effect: Literal["none"] = "none"


_INTENT_FUNCTIONS: dict[HealthIntentKind, tuple[str, str]] = {
    HealthIntentKind.CREATE_NOTE_DRAFT: ("valo.health.create_note_draft", "conversation"),
    HealthIntentKind.LOOKUP_APPOINTMENT: ("valo.health.lookup_appointment_availability", "context"),
    HealthIntentKind.BOOK_APPOINTMENT: ("valo.health.book_appointment", "action"),
    HealthIntentKind.RESCHEDULE_APPOINTMENT: ("valo.health.reschedule_appointment", "action"),
    HealthIntentKind.CANCEL_APPOINTMENT: ("valo.health.cancel_appointment", "action"),
    HealthIntentKind.RENEWAL_REQUEST: ("valo.health.capture_renewal_request", "action"),
}


def propose_health_work(
    intake: HealthIntakeEvidenceV1,
    *,
    correlation_id: str,
    now: datetime,
) -> HealthWorkProposalV1 | None:
    """Turn resolved intent evidence into a bounded Function proposal.

    Confidence is intentionally not an authorization or execution threshold.
    The upstream resolver must mark ambiguity explicitly; ambiguous,
    unsupported, expired, general-question and unknown intake emits no proposal.
    """
    if intake.expires_at <= now:
        return None
    if intake.intent_status is not HealthIntentStatus.RESOLVED:
        return None
    mapped = _INTENT_FUNCTIONS.get(intake.intent)
    if mapped is None:
        return None

    function_id, input_name = mapped
    source_digest = intake.transcript_digest or intake.text_digest
    values = dict(intake.extracted_fields)
    values.update(
        {
            "source_intake_ref": intake.intake_ref,
            "conversation_ref": intake.conversation_ref,
            "source_digest": source_digest,
            "source_evidence_refs": list(intake.evidence_refs),
        }
    )
    if intake.source_artifact_refs:
        values["source_artifact_refs"] = list(intake.source_artifact_refs)

    return HealthWorkProposalV1(
        correlation_id=correlation_id,
        source_intake_ref=intake.intake_ref,
        function_id=function_id,
        input_name=input_name,
        inputs=values,
        evidence_refs=intake.evidence_refs,
    )


def supported_intent_functions() -> dict[str, str]:
    """Read-only deterministic mapping for discovery/tests."""
    return {intent.value: function_id for intent, (function_id, _) in _INTENT_FUNCTIONS.items()}
