"""Health Operations Pack contracts.

The contracts carry health-domain state and evidence only. They deliberately do
not expose authorize/permit/grant/execute surfaces. Consequence-bearing actions
must still compile through Function Fabric / Workflow ISA and cross REHT.
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

SCHEMA_VERSION = "1.0"


def _digest(model: BaseModel) -> str:
    payload = model.model_dump(mode="json", exclude={"schema_version"})
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return f"sha256:{sha256(canonical.encode('utf-8')).hexdigest()}"


def _require_sha256(value: str) -> str:
    if not value.startswith("sha256:") or len(value) != 71:
        raise ValueError("digest must be sha256:<64 hex chars>")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise ValueError("digest must contain hexadecimal sha256 bytes") from exc
    return value.lower()


class HealthModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = SCHEMA_VERSION

    def digest(self) -> str:
        return _digest(self)


class ParticipantKind(StrEnum):
    PATIENT = "patient"
    REPRESENTATIVE = "representative"
    CLINICIAN = "clinician"
    ADMINISTRATOR = "administrator"
    SYSTEM = "system"


class RelationshipKind(StrEnum):
    SELF = "self"
    GUARDIAN = "guardian"
    REPRESENTATIVE = "representative"
    CLINICIAN = "clinician"
    ADMINISTRATOR = "administrator"


class ReviewDisposition(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class AppointmentStatus(StrEnum):
    AVAILABLE = "available"
    BOOKED = "booked"
    RESCHEDULED = "rescheduled"
    CANCELLED = "cancelled"


class RenewalStatus(StrEnum):
    CAPTURED = "captured"
    ROUTED = "routed"
    CLINICAL_REVIEW_REQUESTED = "clinical_review_requested"
    CLINICIAN_DECISION_RECORDED = "clinician_decision_recorded"
    PATIENT_NOTIFIED = "patient_notified"


class ClinicianDecision(StrEnum):
    APPROVE_RENEWAL = "approve_renewal"
    DECLINE_RENEWAL = "decline_renewal"
    CONTACT_PATIENT = "contact_patient"
    REQUIRE_ASSESSMENT = "require_assessment"


class HealthParticipantRefV1(HealthModel):
    participant_ref: str = Field(min_length=1)
    kind: ParticipantKind
    identity_evidence_refs: tuple[str, ...] = Field(default_factory=tuple)
    authority_effect: Literal["none"] = "none"


class HealthRelationshipEvidenceV1(HealthModel):
    relationship_ref: str = Field(min_length=1)
    subject_ref: str = Field(min_length=1)
    patient_ref: str = Field(min_length=1)
    kind: RelationshipKind
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    observed_at: datetime
    valid_until: datetime | None = None
    authority_effect: Literal["none"] = "none"

    @model_validator(mode="after")
    def validate_relationship(self) -> HealthRelationshipEvidenceV1:
        if self.kind is RelationshipKind.SELF and self.subject_ref != self.patient_ref:
            raise ValueError("SELF relationship requires subject_ref == patient_ref")
        if self.valid_until is not None and self.valid_until <= self.observed_at:
            raise ValueError("valid_until must be after observed_at")
        return self


class PatientContextV1(HealthModel):
    patient_ref: str = Field(min_length=1)
    acting_participant_ref: str = Field(min_length=1)
    relationship_ref: str = Field(min_length=1)
    purpose_ref: str = Field(min_length=1)
    observed_at: datetime
    state_version: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = Field(min_length=1)


class EncounterRefV1(HealthModel):
    encounter_ref: str = Field(min_length=1)
    patient_ref: str = Field(min_length=1)
    observed_at: datetime
    state_version: str = Field(min_length=1)


class HealthConversationRefV1(HealthModel):
    conversation_ref: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    started_at: datetime
    source_artifact_refs: tuple[str, ...] = Field(min_length=1)
    transcript_digest: str
    authority_effect: Literal["none"] = "none"

    _validate_transcript_digest = field_validator("transcript_digest")(_require_sha256)


class CandidateClinicalRecordV1(HealthModel):
    candidate_ref: str = Field(min_length=1)
    patient_ref: str = Field(min_length=1)
    encounter_ref: str = Field(min_length=1)
    conversation_ref: str = Field(min_length=1)
    content_ref: str = Field(min_length=1)
    content_digest: str
    source_evidence_refs: tuple[str, ...] = Field(min_length=1)
    created_at: datetime
    candidate_version: str = Field(min_length=1)
    authority_effect: Literal["none"] = "none"

    _validate_content_digest = field_validator("content_digest")(_require_sha256)


class CandidateHealthActionV1(HealthModel):
    action_ref: str = Field(min_length=1)
    function_id: str = Field(min_length=1)
    patient_ref: str = Field(min_length=1)
    actor_ref: str = Field(min_length=1)
    purpose_ref: str = Field(min_length=1)
    destination_ref: str = Field(min_length=1)
    expected_state_version: str = Field(min_length=1)
    payload_digest: str
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    created_at: datetime
    expires_at: datetime
    authority_effect: Literal["none"] = "none"

    _validate_payload_digest = field_validator("payload_digest")(_require_sha256)

    @model_validator(mode="after")
    def validate_window(self) -> CandidateHealthActionV1:
        if self.expires_at <= self.created_at:
            raise ValueError("expires_at must be after created_at")
        return self


class ClinicalReviewAttestationV1(HealthModel):
    review_ref: str = Field(min_length=1)
    reviewer_ref: str = Field(min_length=1)
    patient_ref: str = Field(min_length=1)
    encounter_ref: str = Field(min_length=1)
    candidate_digest: str
    disposition: ReviewDisposition
    reviewed_at: datetime
    valid_until: datetime
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    authority_effect: Literal["none"] = "none"

    _validate_candidate_digest = field_validator("candidate_digest")(_require_sha256)

    @model_validator(mode="after")
    def validate_window(self) -> ClinicalReviewAttestationV1:
        if self.valid_until <= self.reviewed_at:
            raise ValueError("valid_until must be after reviewed_at")
        return self


class AppointmentStateV1(HealthModel):
    appointment_ref: str = Field(min_length=1)
    patient_ref: str = Field(min_length=1)
    status: AppointmentStatus
    slot_ref: str = Field(min_length=1)
    state_version: str = Field(min_length=1)
    observed_at: datetime
    destination_ref: str = Field(min_length=1)


class PrescriptionRenewalRequestV1(HealthModel):
    renewal_ref: str = Field(min_length=1)
    patient_ref: str = Field(min_length=1)
    medication_ref: str = Field(min_length=1)
    status: RenewalStatus
    request_digest: str
    state_version: str = Field(min_length=1)
    captured_at: datetime
    clinician_decision: ClinicianDecision | None = None
    clinician_decision_digest: str | None = None
    authority_effect: Literal["none"] = "none"

    _validate_request_digest = field_validator("request_digest")(_require_sha256)

    @field_validator("clinician_decision_digest")
    @classmethod
    def validate_optional_decision_digest(cls, value: str | None) -> str | None:
        return _require_sha256(value) if value is not None else None

    @model_validator(mode="after")
    def validate_decision_binding(self) -> PrescriptionRenewalRequestV1:
        decision_state = self.status in {
            RenewalStatus.CLINICIAN_DECISION_RECORDED,
            RenewalStatus.PATIENT_NOTIFIED,
        }
        if decision_state and (self.clinician_decision is None or self.clinician_decision_digest is None):
            raise ValueError("clinician decision state requires decision and decision digest")
        if not decision_state and (self.clinician_decision is not None or self.clinician_decision_digest is not None):
            raise ValueError("clinician decision cannot appear before decision state")
        return self


class HealthEffectObservationV1(HealthModel):
    observation_ref: str = Field(min_length=1)
    action_ref: str = Field(min_length=1)
    destination_ref: str = Field(min_length=1)
    observed_at: datetime
    observed_state_digest: str
    observed_state_version: str = Field(min_length=1)
    postcondition_met: bool
    evidence_refs: tuple[str, ...] = Field(min_length=1)
    authority_effect: Literal["none"] = "none"

    _validate_observed_state_digest = field_validator("observed_state_digest")(_require_sha256)
