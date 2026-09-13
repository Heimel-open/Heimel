import pytest

from src.valo_platform.advisor_fabric import (
    AdvisorAuthorityBoundary,
    AdvisorConsentBasis,
    AdvisorContextGateway,
    AdvisorContextRef,
    AdvisorContextScope,
    AdvisorConversationRole,
    AdvisorConversationService,
    AdvisorConversationTurn,
)


def _context_package():
    return AdvisorContextGateway().build_package(
        package_id="pkg-conversation-1",
        role="chro",
        context_refs=[
            AdvisorContextRef(
                ref_id="ctx-1",
                source_type="enterprise_context",
                scope=AdvisorContextScope.TENANT,
                consent_basis=AdvisorConsentBasis.INTERNAL_OPERATIONAL,
                source_ref="enterprise:workforce-risk",
                evidence_refs=["evidence:workforce-risk"],
            )
        ],
    )


def test_start_session_anchors_to_context_package() -> None:
    session = AdvisorConversationService().start_session(
        session_id="session-1",
        context_package=_context_package(),
        initial_human_message="What should we understand about workforce capacity?",
    )

    assert session.advisor_id == "advisor-chro"
    assert session.role == "chro"
    assert session.context_package_id == "pkg-conversation-1"
    assert len(session.turns) == 1
    assert session.turns[0].role == AdvisorConversationRole.HUMAN
    assert session.authority_boundary == AdvisorAuthorityBoundary.ADVISORY_ONLY


def test_append_turn_preserves_existing_session() -> None:
    service = AdvisorConversationService()
    session = service.start_session(
        session_id="session-2",
        context_package=_context_package(),
        initial_human_message="What is the risk?",
    )

    updated = service.append_turn(
        session,
        turn_id="session-2:turn-2",
        role=AdvisorConversationRole.ADVISOR,
        content="The evidence suggests capacity risk needs closer review.",
        artifact_refs=["interp-chro-1"],
    )

    assert len(session.turns) == 1
    assert len(updated.turns) == 2
    assert updated.turns[1].artifact_refs == ["interp-chro-1"]
    assert updated.turns[1].authority_boundary == AdvisorAuthorityBoundary.ADVISORY_ONLY


def test_mentor_prompt_is_advisory_and_references_artifacts() -> None:
    service = AdvisorConversationService()
    session = service.start_session(
        session_id="session-3",
        context_package=_context_package(),
        initial_human_message="Help frame this.",
    )

    prompt = service.mentor_prompt(
        session,
        objective="Prepare options for leadership discussion",
        known_constraints=["No direct HRIS mutation"],
        artifact_refs=["brief-chro-1"],
    )

    assert prompt.role == AdvisorConversationRole.SYSTEM
    assert "Stay advisory-only" in prompt.content
    assert "ActionCaseDraft" in prompt.content
    assert prompt.artifact_refs == ["brief-chro-1"]


def test_summarize_session_is_non_authoritative() -> None:
    service = AdvisorConversationService()
    session = service.start_session(
        session_id="session-4",
        context_package=_context_package(),
        initial_human_message="Summarize.",
    )
    session = service.append_turn(
        session,
        turn_id="session-4:turn-2",
        role=AdvisorConversationRole.ADVISOR,
        content="Briefing ready.",
        artifact_refs=["brief-chro-1", "interp-chro-1"],
    )

    summary = service.summarize_session(session)

    assert summary["turn_count"] == 2
    assert summary["artifact_refs"] == ["brief-chro-1", "interp-chro-1"]
    assert summary["authority_boundary"] == "advisory_only"


def test_empty_turn_content_fails_closed() -> None:
    with pytest.raises(ValueError, match="content cannot be empty"):
        AdvisorConversationTurn(
            turn_id="turn-empty",
            role=AdvisorConversationRole.HUMAN,
            content="   ",
        )


def test_context_package_mismatch_is_rejected() -> None:
    package = _context_package().model_copy(update={"advisor_id": "advisor-ciso"})

    with pytest.raises(ValueError, match="advisor does not match registered profile"):
        AdvisorConversationService().start_session(
            session_id="session-bad",
            context_package=package,
            initial_human_message="Start.",
        )
