import pytest

from src.valo_platform.advisor_fabric import (
    AdvisorAuthorityBoundary,
    AdvisorConsentBasis,
    AdvisorContextGateway,
    AdvisorContextRef,
    AdvisorContextScope,
    AdvisorInterpretationService,
    AdvisorRecommendationService,
    AdvisorRecommendationType,
)


def _interpretation():
    package = AdvisorContextGateway().build_package(
        package_id="pkg-rec-1",
        role="cto",
        context_refs=[
            AdvisorContextRef(
                ref_id="ctx-1",
                source_type="scout_signal",
                scope=AdvisorContextScope.TENANT,
                consent_basis=AdvisorConsentBasis.INTERNAL_OPERATIONAL,
                source_ref="scout:platform-risk",
                evidence_refs=["evidence:platform-risk"],
            )
        ],
    )
    return AdvisorInterpretationService().interpret(
        interpretation_id="interp-cto-1",
        context_package=package,
        stance="The platform risk signal may require a governed remediation proposal.",
        confidence=0.71,
    )


def test_recommendation_defaults_to_non_binding_recommendation() -> None:
    interpretation = _interpretation()

    recommendation = AdvisorRecommendationService().recommend(
        recommendation_id="rec-cto-1",
        interpretation=interpretation,
        statement="Review platform risk before the next release.",
        rationale="The evidence indicates a remediation discussion is warranted.",
    )

    assert recommendation.recommendation_type == AdvisorRecommendationType.RECOMMENDATION
    assert recommendation.requires_action_case is False
    assert recommendation.authority_boundary == AdvisorAuthorityBoundary.ADVISORY_ONLY


def test_recommendation_can_explicitly_request_action_case_draft() -> None:
    interpretation = _interpretation()

    recommendation = AdvisorRecommendationService().recommend(
        recommendation_id="rec-cto-2",
        interpretation=interpretation,
        statement="Prepare a governed remediation proposal.",
        rationale="The remediation could alter production controls.",
        requires_action_case=True,
    )

    assert recommendation.recommendation_type == AdvisorRecommendationType.ACTION_CASE_DRAFT
    assert recommendation.requires_action_case is True
    assert recommendation.source_interpretation_refs == ["interp-cto-1"]


def test_action_case_draft_requires_explicit_action_case_recommendation() -> None:
    interpretation = _interpretation()
    recommendation = AdvisorRecommendationService().recommend(
        recommendation_id="rec-cto-3",
        interpretation=interpretation,
        statement="Review only.",
        rationale="No action case required yet.",
    )

    with pytest.raises(ValueError, match="explicitly require an action case"):
        AdvisorRecommendationService().draft_action_case(
            draft_id="draft-cto-1",
            recommendation=recommendation,
            interpretation=interpretation,
            proposed_action_summary="Prepare remediation.",
        )


def test_action_case_draft_hands_off_to_vaig_with_evidence_refs() -> None:
    interpretation = _interpretation()
    service = AdvisorRecommendationService()
    recommendation = service.recommend(
        recommendation_id="rec-cto-4",
        interpretation=interpretation,
        statement="Prepare a governed remediation proposal.",
        rationale="The remediation could alter production controls.",
        requires_action_case=True,
    )

    draft = service.draft_action_case(
        draft_id="draft-cto-2",
        recommendation=recommendation,
        interpretation=interpretation,
        proposed_action_summary="Evaluate production-control remediation.",
        known_constraints=["Advisor Fabric cannot mutate production controls."],
        missing_inputs=["owner approval context", "rollback plan"],
    )

    assert draft.handoff_target == "VAIG"
    assert draft.evidence_refs == ["evidence:platform-risk"]
    assert draft.originating_advisor_refs == ["advisor-cto"]
    assert draft.authority_boundary == AdvisorAuthorityBoundary.ADVISORY_ONLY
    assert draft.metadata["source_recommendation_id"] == "rec-cto-4"


def test_action_case_draft_rejects_mismatched_interpretation() -> None:
    interpretation = _interpretation()
    service = AdvisorRecommendationService()
    recommendation = service.recommend(
        recommendation_id="rec-cto-5",
        interpretation=interpretation,
        statement="Prepare a governed remediation proposal.",
        rationale="The remediation could alter production controls.",
        requires_action_case=True,
    )
    mismatched = interpretation.model_copy(update={"advisor_id": "advisor-ciso"})

    with pytest.raises(ValueError, match="advisor mismatch"):
        service.draft_action_case(
            draft_id="draft-cto-3",
            recommendation=recommendation,
            interpretation=mismatched,
            proposed_action_summary="Evaluate production-control remediation.",
        )
