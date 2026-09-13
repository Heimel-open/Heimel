import pytest
from pydantic import ValidationError

from valo_operator.frontline import (
    CandidateOperation,
    FrontlineEnvelope,
    FrontlineModality,
    KnowledgeCandidate,
    bind_candidate_operation,
)


def test_frontline_accepts_low_friction_text_photo_and_voice_inputs():
    text = FrontlineEnvelope(
        interaction_id="i-text",
        channel="sms",
        channel_actor_ref="phone:+10000000000",
        modality=FrontlineModality.TEXT,
        received_at="2026-08-08T18:00:00Z",
        text="Machine 12 stopped. What should I check?",
    )
    photo = FrontlineEnvelope(
        interaction_id="i-photo",
        channel="sms",
        channel_actor_ref="phone:+10000000000",
        modality=FrontlineModality.PHOTO,
        received_at="2026-08-08T18:00:01Z",
        artifact_refs=("sha256:photo",),
    )
    voice = FrontlineEnvelope(
        interaction_id="i-voice",
        channel="sms",
        channel_actor_ref="phone:+10000000000",
        modality=FrontlineModality.VOICE,
        received_at="2026-08-08T18:00:02Z",
        artifact_refs=("sha256:voice",),
    )

    assert text.authority_effect == photo.authority_effect == voice.authority_effect == "none"


def test_channel_identity_never_becomes_operator_authority():
    envelope = FrontlineEnvelope(
        interaction_id="i-1",
        channel="sms",
        channel_actor_ref="phone:+10000000000",
        modality="text",
        received_at="2026-08-08T18:00:00Z",
        text="Create a maintenance work order",
    )
    dumped = envelope.model_dump()
    assert "session" not in dumped
    assert "permit" not in dumped
    assert dumped["authority_effect"] == "none"


def test_photo_and_voice_require_artifact_provenance():
    with pytest.raises(ValidationError):
        FrontlineEnvelope(
            interaction_id="i-photo",
            channel="sms",
            channel_actor_ref="worker-1",
            modality="photo",
            received_at="2026-08-08T18:00:00Z",
            text="looks wrong",
        )


def test_captured_tribal_knowledge_requires_provenance_and_freshness():
    knowledge = KnowledgeCandidate(
        knowledge_id="k-1",
        source_interaction_id="i-1",
        source_actor_ref="manager-1",
        statement="Reset only after pressure is below the approved threshold.",
        provenance_refs=("interaction:i-1", "sop:rev-7"),
        observed_at="2026-08-08T18:00:00Z",
        fresh_until="2026-09-08T18:00:00Z",
        verification_status="corroborated",
    )
    assert knowledge.authority_effect == "none"

    with pytest.raises(ValidationError):
        KnowledgeCandidate(
            knowledge_id="k-2",
            source_interaction_id="i-2",
            source_actor_ref="manager-1",
            statement="Do this forever.",
            provenance_refs=(),
            observed_at="2026-08-08T18:00:00Z",
            fresh_until="2026-09-08T18:00:00Z",
        )


def test_candidate_operation_compiles_only_to_registered_function_request():
    operation = CandidateOperation(
        correlation_id="corr-1",
        source_interaction_id="i-1",
        function_id="maintenance.create_work_order",
        function_version="1.2.0",
        inputs={"asset_id": "machine-12", "priority": "high"},
        route_hint="cmms",
    )
    request = bind_candidate_operation(operation)

    assert request.function_id == "maintenance.create_work_order"
    assert request.function_version == "1.2.0"
    assert request.inputs == {"asset_id": "machine-12", "priority": "high"}
    assert "authority_effect" not in request.model_dump()
    assert "requires_fresh_reht" not in request.model_dump()


def test_frontline_candidate_cannot_disable_fresh_reht_or_invent_authority():
    with pytest.raises(ValidationError):
        CandidateOperation(
            correlation_id="corr-1",
            source_interaction_id="i-1",
            function_id="maintenance.create_work_order",
            requires_fresh_reht=False,
        )

    with pytest.raises(ValidationError):
        CandidateOperation.model_validate(
            {
                "correlation_id": "corr-1",
                "source_interaction_id": "i-1",
                "function_id": "maintenance.create_work_order",
                "authority": "allow",
            }
        )
