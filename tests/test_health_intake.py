from datetime import UTC, datetime, timedelta

from valo_health_pack import (
    HealthIntakeEvidenceV1,
    HealthIntakeModality,
    HealthIntentKind,
    HealthIntentStatus,
    propose_health_work,
    supported_intent_functions,
)
from valo_health_pack.world import seed_world
from valo_operator import bind_candidate_operation, bind_health_work_proposal, build_health_runtime

NOW = datetime(2026, 8, 10, 12, 0, tzinfo=UTC)
D1 = "sha256:" + "1" * 64
D2 = "sha256:" + "2" * 64


def _voice_intake(
    *,
    intent: HealthIntentKind,
    status: HealthIntentStatus = HealthIntentStatus.RESOLVED,
    confidence: float | None = 0.99,
    fields: dict | None = None,
) -> HealthIntakeEvidenceV1:
    return HealthIntakeEvidenceV1(
        intake_ref="intake-1",
        conversation_ref="call-1",
        modality=HealthIntakeModality.VOICE,
        channel="telephone",
        source_artifact_refs=("audio:1",),
        transcript_digest=D1,
        intent=intent,
        intent_status=status,
        intent_confidence=confidence,
        intent_method_ref="intent-router:v1",
        extracted_fields=fields or {},
        evidence_refs=("transcript:1", "call:1"),
        observed_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )


def test_resolved_voice_booking_becomes_candidate_operation_not_authority():
    intake = _voice_intake(
        intent=HealthIntentKind.BOOK_APPOINTMENT,
        fields={
            "patient_ref": "patient-1",
            "appointment_ref": "appointment-1",
            "slot_ref": "slot-1",
            "payload_digest": D2,
        },
    )
    proposal = propose_health_work(intake, correlation_id="corr-book", now=NOW)

    assert proposal is not None
    assert proposal.authority_effect == "none"
    assert proposal.function_id == "valo.health.book_appointment"
    assert proposal.requires_fresh_reht is True

    operation = bind_health_work_proposal(proposal)
    assert operation.authority_effect == "none"
    assert operation.requires_fresh_reht is True
    assert operation.route_hint == "health"
    assert "permit" not in operation.model_dump()
    assert "authority" not in operation.model_dump()


def test_high_confidence_ambiguous_voice_intent_emits_no_operation():
    intake = _voice_intake(
        intent=HealthIntentKind.BOOK_APPOINTMENT,
        status=HealthIntentStatus.AMBIGUOUS,
        confidence=1.0,
    )

    assert propose_health_work(intake, correlation_id="corr-ambiguous", now=NOW) is None


def test_general_question_never_maps_to_consequential_function():
    intake = _voice_intake(
        intent=HealthIntentKind.GENERAL_QUESTION,
        confidence=1.0,
    )

    assert propose_health_work(intake, correlation_id="corr-question", now=NOW) is None
    assert "general_question" not in supported_intent_functions()


def test_expired_intake_cannot_reenter_as_candidate_work():
    intake = _voice_intake(intent=HealthIntentKind.RENEWAL_REQUEST).model_copy(
        update={"observed_at": NOW - timedelta(minutes=10), "expires_at": NOW - timedelta(minutes=1)}
    )

    assert propose_health_work(intake, correlation_id="corr-expired", now=NOW) is None


def test_voice_intake_to_operator_still_requires_real_reht_authority():
    intake = _voice_intake(
        intent=HealthIntentKind.BOOK_APPOINTMENT,
        fields={
            "patient_ref": "patient-1",
            "appointment_ref": "appointment-1",
            "slot_ref": "slot-1",
            "payload_digest": D2,
        },
    )
    proposal = propose_health_work(intake, correlation_id="corr-live", now=NOW)
    assert proposal is not None
    request = bind_candidate_operation(bind_health_work_proposal(proposal))

    allowed = build_health_runtime().submit(request)
    denied = build_health_runtime(kernel=seed_world(revoke_appointment_authority=True)).submit(request)

    assert allowed.decision == "ALLOW"
    assert allowed.effect_verified is True
    assert denied.decision == "DENY"
    assert denied.gateway_executions == 0


def test_renewal_request_maps_only_to_capture_not_clinical_decision_or_execution():
    intake = _voice_intake(
        intent=HealthIntentKind.RENEWAL_REQUEST,
        fields={"patient_ref": "patient-1", "renewal_ref": "renewal-1", "payload_digest": D2},
    )
    proposal = propose_health_work(intake, correlation_id="corr-renewal", now=NOW)

    assert proposal is not None
    assert proposal.function_id == "valo.health.capture_renewal_request"
    assert "record_clinician_decision" not in proposal.function_id
    assert "execute_authorized_prescription" not in proposal.function_id


def test_text_intake_requires_digest_and_maps_to_same_registered_surface():
    intake = HealthIntakeEvidenceV1(
        intake_ref="text-1",
        conversation_ref="chat-1",
        modality=HealthIntakeModality.TEXT,
        channel="web",
        text_digest=D1,
        intent=HealthIntentKind.CANCEL_APPOINTMENT,
        intent_status=HealthIntentStatus.RESOLVED,
        intent_confidence=None,
        intent_method_ref="intent-router:v1",
        extracted_fields={"appointment_ref": "appointment-1", "payload_digest": D2},
        evidence_refs=("chat:1",),
        observed_at=NOW,
        expires_at=NOW + timedelta(minutes=5),
    )
    proposal = propose_health_work(intake, correlation_id="corr-text", now=NOW)

    assert proposal is not None
    assert proposal.function_id == "valo.health.cancel_appointment"
    assert proposal.authority_effect == "none"
