"""Fail-closed health-domain admissibility checks.

These checks decide only whether domain prerequisites are satisfied. They never
mint a REHT permit or authorize execution.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .contracts import (
    CandidateClinicalRecordV1,
    CandidateHealthActionV1,
    ClinicalReviewAttestationV1,
    HealthRelationshipEvidenceV1,
    PatientContextV1,
    RelationshipKind,
    RenewalStatus,
    ReviewDisposition,
)


class DomainAdmissibilityStatus(StrEnum):
    ADMISSIBLE = "admissible"
    STEP_UP_REQUIRED = "step_up_required"
    REJECTED = "rejected"


class DomainAdmissibilityResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    status: DomainAdmissibilityStatus
    reason: str
    evidence_refs: tuple[str, ...] = ()
    authority_effect: Literal["none"] = "none"

    @property
    def admissible(self) -> bool:
        return self.status is DomainAdmissibilityStatus.ADMISSIBLE


def evaluate_patient_context(
    context: PatientContextV1,
    relationship: HealthRelationshipEvidenceV1,
    *,
    now: datetime,
) -> DomainAdmissibilityResult:
    if relationship.patient_ref != context.patient_ref:
        return _reject("relationship patient does not match context")
    if relationship.subject_ref != context.acting_participant_ref:
        return _reject("relationship subject does not match acting participant")
    if relationship.relationship_ref != context.relationship_ref:
        return _reject("relationship reference does not match context")
    if relationship.observed_at > now:
        return _reject("relationship observation is from the future")
    if relationship.valid_until is not None and relationship.valid_until <= now:
        return _step_up("relationship evidence is expired", relationship.evidence_refs)
    if relationship.kind is not RelationshipKind.SELF and not relationship.evidence_refs:
        return _step_up("acting-for-another relationship requires evidence")
    return _admit("patient context relationship prerequisites satisfied", relationship.evidence_refs)


def evaluate_candidate_action(
    action: CandidateHealthActionV1,
    context: PatientContextV1,
    *,
    current_state_version: str,
    now: datetime,
) -> DomainAdmissibilityResult:
    if action.patient_ref != context.patient_ref:
        return _reject("action patient does not match current patient context")
    if action.actor_ref != context.acting_participant_ref:
        return _reject("action actor does not match current acting participant")
    if action.purpose_ref != context.purpose_ref:
        return _reject("action purpose changed")
    if action.expected_state_version != current_state_version:
        return _reject("expected state version is stale")
    if action.created_at > now:
        return _reject("candidate action was created in the future")
    if action.expires_at <= now:
        return _reject("candidate action expired")
    return _admit("candidate action is bound to current patient, actor, purpose, and state", action.evidence_refs)


def evaluate_clinical_note_commit(
    candidate: CandidateClinicalRecordV1,
    review: ClinicalReviewAttestationV1,
    *,
    now: datetime,
) -> DomainAdmissibilityResult:
    if review.disposition is not ReviewDisposition.APPROVED:
        return _reject("clinical note review did not approve the candidate")
    if review.patient_ref != candidate.patient_ref:
        return _reject("review patient does not match candidate patient")
    if review.encounter_ref != candidate.encounter_ref:
        return _reject("review encounter does not match candidate encounter")
    if review.candidate_digest != candidate.digest():
        return _reject("review is not bound to the exact current candidate digest")
    if review.reviewed_at > now:
        return _reject("clinical review is from the future")
    if review.valid_until <= now:
        return _reject("clinical review expired before commit")
    return _admit("exact candidate has a current clinician approval", review.evidence_refs)


_ALLOWED_RENEWAL_TRANSITIONS: dict[RenewalStatus, RenewalStatus] = {
    RenewalStatus.CAPTURED: RenewalStatus.ROUTED,
    RenewalStatus.ROUTED: RenewalStatus.CLINICAL_REVIEW_REQUESTED,
    RenewalStatus.CLINICAL_REVIEW_REQUESTED: RenewalStatus.CLINICIAN_DECISION_RECORDED,
    RenewalStatus.CLINICIAN_DECISION_RECORDED: RenewalStatus.PATIENT_NOTIFIED,
}


def evaluate_renewal_transition(
    current: RenewalStatus,
    requested: RenewalStatus,
) -> DomainAdmissibilityResult:
    expected = _ALLOWED_RENEWAL_TRANSITIONS.get(current)
    if expected is None:
        return _reject(f"renewal state {current.value} is terminal")
    if requested is not expected:
        return _reject(f"renewal transition must be {current.value} -> {expected.value}")
    return _admit(f"renewal transition {current.value} -> {requested.value} is structurally valid")


def _admit(reason: str, evidence_refs: tuple[str, ...] = ()) -> DomainAdmissibilityResult:
    return DomainAdmissibilityResult(
        status=DomainAdmissibilityStatus.ADMISSIBLE,
        reason=reason,
        evidence_refs=evidence_refs,
    )


def _step_up(reason: str, evidence_refs: tuple[str, ...] = ()) -> DomainAdmissibilityResult:
    return DomainAdmissibilityResult(
        status=DomainAdmissibilityStatus.STEP_UP_REQUIRED,
        reason=reason,
        evidence_refs=evidence_refs,
    )


def _reject(reason: str) -> DomainAdmissibilityResult:
    return DomainAdmissibilityResult(status=DomainAdmissibilityStatus.REJECTED, reason=reason)
