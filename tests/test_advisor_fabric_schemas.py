import pytest
from pydantic import ValidationError

from src.valo_platform.advisor_fabric import (
    ActionCaseDraft,
    AdvisorAuthorityBoundary,
    AdvisorInterpretation,
    AdvisorMemoryPolicy,
    AdvisorProfile,
    AdvisorRecommendation,
    AdvisorRecommendationType,
)


def test_advisor_profile_is_advisory_only_by_default() -> None:
    profile = AdvisorProfile(
        advisor_id="advisor-ciso",
        version="2026-07-17",
        role="ciso",
        purpose="Interpret security posture and explain risks",
        allowed_inputs=["scout_signal", "baro_evidence"],
        allowed_outputs=[
            AdvisorRecommendationType.INSIGHT,
            AdvisorRecommendationType.ACTION_CASE_DRAFT,
        ],
        evidence_policy="cite source evidence refs",
        memory_policy=AdvisorMemoryPolicy.TENANT_SCOPED,
    )

    assert profile.authority_boundary == AdvisorAuthorityBoundary.ADVISORY_ONLY
    assert AdvisorRecommendationType.ACTION_CASE_DRAFT in profile.allowed_outputs


def test_interpretation_carries_evidence_without_authority() -> None:
    interpretation = AdvisorInterpretation(
        interpretation_id="interp-1",
        advisor_id="advisor-cfo",
        source_evidence_refs=["baro:risk:42"],
        lineage_id="lineage-1",
        stance="Budget exposure is rising faster than operating context explains.",
        confidence=0.72,
        limitations=["Only one quarter of spend data is available."],
        questions_for_human=["Should committed renewals be included?"],
    )

    assert interpretation.source_evidence_refs == ["baro:risk:42"]
    assert interpretation.confidence == 0.72
    assert interpretation.authority_boundary == AdvisorAuthorityBoundary.ADVISORY_ONLY


def test_action_case_recommendations_must_be_explicit() -> None:
    with pytest.raises(ValidationError):
        AdvisorRecommendation(
            recommendation_id="rec-1",
            advisor_id="advisor-coo",
            source_interpretation_refs=["interp-1"],
            recommendation_type=AdvisorRecommendationType.ACTION_CASE_DRAFT,
            statement="Prepare a governed remediation proposal.",
            rationale="The operational signal is material.",
        )

    recommendation = AdvisorRecommendation(
        recommendation_id="rec-2",
        advisor_id="advisor-coo",
        source_interpretation_refs=["interp-1"],
        recommendation_type=AdvisorRecommendationType.ACTION_CASE_DRAFT,
        statement="Prepare a governed remediation proposal.",
        rationale="The operational signal is material.",
        requires_action_case=True,
    )

    assert recommendation.requires_action_case is True
    assert recommendation.authority_boundary == AdvisorAuthorityBoundary.ADVISORY_ONLY


def test_action_case_draft_hands_off_to_vaig_only() -> None:
    draft = ActionCaseDraft(
        draft_id="draft-1",
        originating_advisor_refs=["advisor-ciso"],
        evidence_refs=["scout:signal:1", "baro:evidence:2"],
        proposed_action_summary="Review privileged access rotation exception.",
        known_constraints=["No direct external mutation from Advisor Fabric."],
        missing_inputs=["manager approval context"],
    )

    assert draft.handoff_target == "VAIG"
    assert draft.authority_boundary == AdvisorAuthorityBoundary.ADVISORY_ONLY

    with pytest.raises(ValidationError):
        ActionCaseDraft(
            draft_id="draft-2",
            proposed_action_summary="Route somewhere else.",
            handoff_target="Core",
        )


def test_advisor_schemas_do_not_expose_execution_authority_fields() -> None:
    forbidden_fields = {
        "clearance_id",
        "permit_id",
        "decision",
        "authorized",
        "can_execute",
        "allowed_to_execute",
        "execution_authorized",
    }

    for model in (
        AdvisorProfile,
        AdvisorInterpretation,
        AdvisorRecommendation,
        ActionCaseDraft,
    ):
        assert forbidden_fields.isdisjoint(model.model_fields)
