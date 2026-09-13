"""Shared interpretation and briefing service for Advisor Fabric.

The service turns a validated AdvisorContextPackage into advisory artifacts. It
does not score admissibility, issue decisions or call external systems.
"""

from typing import List, Optional, Sequence

from .context_gateway import AdvisorContextPackage
from .profiles import get_advisor_profile
from .schemas import (
    AdvisorInterpretation,
    AdvisorRecommendation,
    AdvisorRecommendationType,
)


class AdvisorInterpretationService:
    """Create non-binding Advisor interpretations and briefings."""

    def interpret(
        self,
        *,
        interpretation_id: str,
        context_package: AdvisorContextPackage,
        stance: str,
        confidence: float,
        limitations: Optional[Sequence[str]] = None,
        questions_for_human: Optional[Sequence[str]] = None,
    ) -> AdvisorInterpretation:
        self._assert_known_profile(context_package)
        evidence_refs = self._collect_evidence_refs(context_package)

        return AdvisorInterpretation(
            interpretation_id=interpretation_id,
            advisor_id=context_package.advisor_id,
            source_evidence_refs=evidence_refs,
            lineage_id=context_package.package_id,
            stance=stance,
            confidence=confidence,
            limitations=list(context_package.limitations) + list(limitations or ()),
            questions_for_human=list(questions_for_human or ()),
        )

    def briefing(
        self,
        *,
        recommendation_id: str,
        interpretation: AdvisorInterpretation,
        statement: str,
        rationale: str,
        risk_notes: Optional[Sequence[str]] = None,
    ) -> AdvisorRecommendation:
        return AdvisorRecommendation(
            recommendation_id=recommendation_id,
            advisor_id=interpretation.advisor_id,
            source_interpretation_refs=[interpretation.interpretation_id],
            recommendation_type=AdvisorRecommendationType.BRIEFING,
            statement=statement,
            rationale=rationale,
            risk_notes=list(risk_notes or ()),
            requires_action_case=False,
        )

    @staticmethod
    def _assert_known_profile(context_package: AdvisorContextPackage) -> None:
        profile = get_advisor_profile(context_package.role)
        if profile.advisor_id != context_package.advisor_id:
            raise ValueError("context package advisor does not match registered profile")

    @staticmethod
    def _collect_evidence_refs(context_package: AdvisorContextPackage) -> List[str]:
        refs: List[str] = []
        for context_ref in context_package.context_refs:
            refs.extend(context_ref.evidence_refs)
        for memory_ref in context_package.memory_refs:
            refs.extend(memory_ref.evidence_refs)
        return list(dict.fromkeys(refs))
