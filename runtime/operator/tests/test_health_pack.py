from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from valo_health_pack import (
    RESERVED_FUNCTION_IDS,
    AppointmentStateV1,
    AppointmentStatus,
    CandidateClinicalRecordV1,
    CandidateHealthActionV1,
    ClinicalReviewAttestationV1,
    ClinicianDecision,
    DomainAdmissibilityStatus,
    HealthConversationRefV1,
    HealthRelationshipEvidenceV1,
    PatientContextV1,
    PrescriptionRenewalRequestV1,
    RelationshipKind,
    RenewalStatus,
    ReviewDisposition,
    build_health_registry,
    evaluate_candidate_action,
    evaluate_clinical_note_commit,
    evaluate_patient_context,
    evaluate_renewal_transition,
    health_function_ids,
)

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64
D3 = "sha256:" + "3" * 64


def _context() -> PatientContextV1:
    return PatientContextV1(
        patient_ref="patient-1",
        acting_participant_ref="patient-1",
        relationship_ref="rel-self-1",
        purpose_ref="purpose-care-admin",
        observed_at=NOW,
        state_version="v7",
        evidence_refs=("identity:verified-1",),
    )


def _candidate() -> CandidateClinicalRecordV1:
    return CandidateClinicalRecordV1(
        candidate_ref="note-candidate-1",
        patient_ref="patient-1",
        encounter_ref="encounter-1",
        conversation_ref="conversation-1",
        content_ref="health-artifact:note-1",
        content_digest=D1,
        source_evidence_refs=("transcript:t-1",),
        created_at=NOW,
        candidate_version="1",
    )


def test_contract_digests_are_deterministic_and_content_bound():
    first = _candidate()
    second = _candidate()
    changed = first.model_copy(update={"content_digest": D2})

    assert first.digest() == second.digest()
    assert first.digest() != changed.digest()


def test_raw_conversation_is_reference_only_and_has_no_authority_effect():
    conversation = HealthConversationRefV1(
        conversation_ref="conversation-1",
        channel="voice",
        started_at=NOW,
        source_artifact_refs=("audio:sha256-1",),
        transcript_digest=D1,
    )
    dumped = conversation.model_dump()

    assert dumped["authority_effect"] == "none"
    assert "raw_audio" not in dumped
    assert "transcript_text" not in dumped


def test_self_relationship_requires_same_subject_and_patient():
    with pytest.raises(ValidationError):
        HealthRelationshipEvidenceV1(
            relationship_ref="rel-bad",
            subject_ref="representative-1",
            patient_ref="patient-1",
            kind=RelationshipKind.SELF,
            evidence_refs=("identity:e1",),
            observed_at=NOW,
        )


def test_expired_relationship_steps_up_instead_of_falling_back_to_self():
    relationship = HealthRelationshipEvidenceV1(
        relationship_ref="rel-self-1",
        subject_ref="patient-1",
        patient_ref="patient-1",
        kind=RelationshipKind.SELF,
        evidence_refs=("identity:e1",),
        observed_at=NOW - timedelta(days=2),
        valid_until=NOW - timedelta(seconds=1),
    )
    result = evaluate_patient_context(_context(), relationship, now=NOW)

    assert result.status is DomainAdmissibilityStatus.STEP_UP_REQUIRED
    assert result.authority_effect == "none"


def test_candidate_action_is_bound_to_patient_actor_purpose_state_and_expiry():
    action = CandidateHealthActionV1(
        action_ref="action-1",
        function_id="valo.health.book_appointment",
        patient_ref="patient-1",
        actor_ref="patient-1",
        purpose_ref="purpose-care-admin",
        destination_ref="schedule-1",
        expected_state_version="v7",
        payload_digest=D2,
        evidence_refs=("conversation:1",),
        created_at=NOW - timedelta(seconds=2),
        expires_at=NOW + timedelta(minutes=2),
    )

    assert evaluate_candidate_action(action, _context(), current_state_version="v7", now=NOW).admissible
    stale = evaluate_candidate_action(action, _context(), current_state_version="v8", now=NOW)
    assert stale.status is DomainAdmissibilityStatus.REJECTED


def test_note_commit_requires_exact_current_candidate_digest():
    candidate = _candidate()
    review = ClinicalReviewAttestationV1(
        review_ref="review-1",
        reviewer_ref="clinician-1",
        patient_ref="patient-1",
        encounter_ref="encounter-1",
        candidate_digest=candidate.digest(),
        disposition=ReviewDisposition.APPROVED,
        reviewed_at=NOW,
        valid_until=NOW + timedelta(minutes=10),
        evidence_refs=("review-ui:receipt-1",),
    )

    assert evaluate_clinical_note_commit(candidate, review, now=NOW + timedelta(seconds=1)).admissible

    edited = candidate.model_copy(update={"content_digest": D3})
    result = evaluate_clinical_note_commit(edited, review, now=NOW + timedelta(seconds=1))
    assert result.status is DomainAdmissibilityStatus.REJECTED


def test_rejected_clinician_review_never_admits_note_commit():
    candidate = _candidate()
    review = ClinicalReviewAttestationV1(
        review_ref="review-2",
        reviewer_ref="clinician-1",
        patient_ref="patient-1",
        encounter_ref="encounter-1",
        candidate_digest=candidate.digest(),
        disposition=ReviewDisposition.REJECTED,
        reviewed_at=NOW,
        valid_until=NOW + timedelta(minutes=10),
        evidence_refs=("review-ui:receipt-2",),
    )

    result = evaluate_clinical_note_commit(candidate, review, now=NOW + timedelta(seconds=1))
    assert result.status is DomainAdmissibilityStatus.REJECTED


def test_renewal_workflow_cannot_skip_from_capture_to_clinician_decision():
    assert evaluate_renewal_transition(RenewalStatus.CAPTURED, RenewalStatus.ROUTED).admissible
    skipped = evaluate_renewal_transition(
        RenewalStatus.CAPTURED,
        RenewalStatus.CLINICIAN_DECISION_RECORDED,
    )
    assert skipped.status is DomainAdmissibilityStatus.REJECTED


def test_decision_state_requires_bound_clinician_decision_digest():
    with pytest.raises(ValidationError):
        PrescriptionRenewalRequestV1(
            renewal_ref="renewal-1",
            patient_ref="patient-1",
            medication_ref="medication-1",
            status=RenewalStatus.CLINICIAN_DECISION_RECORDED,
            request_digest=D1,
            state_version="r3",
            captured_at=NOW,
        )

    valid = PrescriptionRenewalRequestV1(
        renewal_ref="renewal-1",
        patient_ref="patient-1",
        medication_ref="medication-1",
        status=RenewalStatus.CLINICIAN_DECISION_RECORDED,
        request_digest=D1,
        state_version="r3",
        captured_at=NOW,
        clinician_decision=ClinicianDecision.CONTACT_PATIENT,
        clinician_decision_digest=D2,
    )
    assert valid.authority_effect == "none"


def test_appointment_state_is_versioned_and_destination_bound():
    appointment = AppointmentStateV1(
        appointment_ref="appointment-1",
        patient_ref="patient-1",
        status=AppointmentStatus.BOOKED,
        slot_ref="slot-2026-08-11T09:00",
        state_version="a2",
        observed_at=NOW,
        destination_ref="schedule-1",
    )
    assert appointment.digest().startswith("sha256:")


def test_registry_contains_distinct_health_effects_and_no_prescription_execution():
    registry = build_health_registry()
    function_ids = health_function_ids()

    assert len(function_ids) == 12
    assert registry.validate() == []
    assert "valo.health.capture_renewal_request" in function_ids
    assert "valo.health.route_renewal_request" in function_ids
    assert "valo.health.request_clinical_review" in function_ids
    assert "valo.health.record_clinician_decision" in function_ids
    assert RESERVED_FUNCTION_IDS == ("valo.health.execute_authorized_prescription_action",)
    assert RESERVED_FUNCTION_IDS[0] not in function_ids


def test_registered_commit_and_clinician_decision_require_separate_capabilities():
    registry = build_health_registry()
    commit = registry.resolve("valo.health.commit_clinical_note", "1.0.0")
    decision = registry.resolve("valo.health.record_clinician_decision", "1.0.0")

    assert commit.authority_requirements[0].capability == "CLINICAL_RECORD_WRITE"
    assert decision.authority_requirements[0].capability == "CLINICAL_DECISION_RECORD"
    assert commit.authority_requirements[0].capability != decision.authority_requirements[0].capability


def test_health_pack_exposes_no_authority_minting_surface():
    import valo_health_pack

    forbidden = {"authorize", "permit", "grant_authority", "execute"}
    public = {name.lower() for name in dir(valo_health_pack) if not name.startswith("_")}
    assert forbidden.isdisjoint(public)
