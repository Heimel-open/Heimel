"""Recommendation and ActionCaseDraft service for Advisor Fabric."""

from typing import Optional, Sequence

from .schemas import (
    ActionCaseDraft,
    AdvisorInterpretation,
    AdvisorRecommendation,
    AdvisorRecommendationType,
)


class AdvisorRecommendationService:
    """Create non-binding recommendations and optional action-case drafts."""

    def recommend(
        self,
        *,
        recommendation_id: str,
        interpretation: AdvisorInterpretation,
        statement: str,
        rationale: str,
        risk_notes: Optional[Sequence[str]] = None,
        requires_action_case: bool = False,
    ) -> AdvisorRecommendation:
        recommendation_type = (
            AdvisorRecommendationType.ACTION_CASE_DRAFT
            if requires_action_case
            else AdvisorRecommendationType.RECOMMENDATION
        )
        return AdvisorRecommendation(
            recommendation_id=recommendation_id,
            advisor_id=interpretation.advisor_id,
            source_interpretation_refs=[interpretation.interpretation_id],
            recommendation_type=recommendation_type,
            statement=statement,
            rationale=rationale,
            risk_notes=list(risk_notes or ()),
            requires_action_case=requires_action_case,
        )

    def draft_action_case(
        self,
        *,
        draft_id: str,
        recommendation: AdvisorRecommendation,
        interpretation: AdvisorInterpretation,
        proposed_action_summary: str,
        known_constraints: Optional[Sequence[str]] = None,
        missing_inputs: Optional[Sequence[str]] = None,
    ) -> ActionCaseDraft:
        if not recommendation.requires_action_case:
            raise ValueError("recommendation must explicitly require an action case")
        if recommendation.recommendation_type != AdvisorRecommendationType.ACTION_CASE_DRAFT:
            raise ValueError("recommendation must use action_case_draft type")
        if recommendation.advisor_id != interpretation.advisor_id:
            raise ValueError("recommendation and interpretation advisor mismatch")
        if interpretation.interpretation_id not in recommendation.source_interpretation_refs:
            raise ValueError("recommendation must reference the source interpretation")

        return ActionCaseDraft(
            draft_id=draft_id,
            originating_advisor_refs=[recommendation.advisor_id],
            evidence_refs=list(interpretation.source_evidence_refs),
            proposed_action_summary=proposed_action_summary,
            known_constraints=list(known_constraints or ()),
            missing_inputs=list(missing_inputs or ()),
            metadata={"source_recommendation_id": recommendation.recommendation_id},
        )
