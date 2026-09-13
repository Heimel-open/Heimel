"""Outcome tracking and follow-up contracts for Advisor Fabric.

These models keep the follow-up layer advisory-only. They record what was
observed after a recommendation, but they do not introduce execution authority
or governed actions.
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Sequence

from pydantic import BaseModel, ConfigDict, Field

from .schemas import AdvisorAuthorityBoundary, AdvisorInterpretation, AdvisorRecommendation


class AdvisorOutcomeStatus(str, Enum):
    """Observed result of an advisory recommendation."""

    PENDING = "pending"
    OBSERVED = "observed"
    MITIGATED = "mitigated"
    REALIZED = "realized"
    NO_THREAT = "no_threat"
    NEEDS_REVIEW = "needs_review"


class AdvisorFollowupAction(str, Enum):
    """Non-binding action to take after an outcome is recorded."""

    RETAIN = "retain"
    REVIEW = "review"
    LEARN = "learn"
    ESCALATE_TO_HUMAN = "escalate_to_human"


class AdvisorOutcomeRecord(BaseModel):
    """Recorded outcome for a recommendation."""

    outcome_id: str
    recommendation_id: str
    advisor_id: str
    status: AdvisorOutcomeStatus
    observed_at: datetime = Field(default_factory=datetime.utcnow)
    outcome_summary: str
    evidence_refs: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    human_review_required: bool = False
    authority_boundary: AdvisorAuthorityBoundary = AdvisorAuthorityBoundary.ADVISORY_ONLY

    model_config = ConfigDict(use_enum_values=False)


class AdvisorFollowupNote(BaseModel):
    """Advisor-only follow-up note derived from an outcome."""

    note_id: str
    outcome_id: str
    advisor_id: str
    action: AdvisorFollowupAction
    message: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    authority_boundary: AdvisorAuthorityBoundary = AdvisorAuthorityBoundary.ADVISORY_ONLY
    evidence_refs: List[str] = Field(default_factory=list)

    model_config = ConfigDict(use_enum_values=False)


class AdvisorFollowupBundle(BaseModel):
    """Convenience bundle that pairs an outcome with its follow-up note."""

    bundle_id: str
    outcome: AdvisorOutcomeRecord
    followup_note: AdvisorFollowupNote
    created_at: datetime = Field(default_factory=datetime.utcnow)
    authority_boundary: AdvisorAuthorityBoundary = AdvisorAuthorityBoundary.ADVISORY_ONLY

    model_config = ConfigDict(use_enum_values=False)


class AdvisorFollowupService:
    """Create advisory outcome records and non-binding follow-up notes."""

    def record_outcome(
        self,
        *,
        outcome_id: str,
        recommendation: AdvisorRecommendation,
        interpretation: AdvisorInterpretation,
        status: AdvisorOutcomeStatus,
        outcome_summary: str,
        evidence_refs: Optional[Sequence[str]] = None,
        notes: Optional[Sequence[str]] = None,
        human_review_required: bool = False,
        observed_at: Optional[datetime] = None,
    ) -> AdvisorOutcomeRecord:
        self._assert_alignment(recommendation, interpretation)

        return AdvisorOutcomeRecord(
            outcome_id=outcome_id,
            recommendation_id=recommendation.recommendation_id,
            advisor_id=recommendation.advisor_id,
            status=status,
            observed_at=observed_at or datetime.utcnow(),
            outcome_summary=outcome_summary,
            evidence_refs=list(evidence_refs or ()),
            notes=list(notes or ()),
            human_review_required=human_review_required,
        )

    def followup_note(
        self,
        *,
        note_id: str,
        outcome: AdvisorOutcomeRecord,
        message: Optional[str] = None,
        evidence_refs: Optional[Sequence[str]] = None,
        created_at: Optional[datetime] = None,
    ) -> AdvisorFollowupNote:
        action = self._derive_action(outcome)
        return AdvisorFollowupNote(
            note_id=note_id,
            outcome_id=outcome.outcome_id,
            advisor_id=outcome.advisor_id,
            action=action,
            message=message or self._build_message(outcome, action),
            created_at=created_at or datetime.utcnow(),
            evidence_refs=list(evidence_refs or outcome.evidence_refs),
        )

    def bundle(
        self,
        *,
        bundle_id: str,
        outcome: AdvisorOutcomeRecord,
        followup_note: AdvisorFollowupNote,
        created_at: Optional[datetime] = None,
    ) -> AdvisorFollowupBundle:
        if outcome.outcome_id != followup_note.outcome_id:
            raise ValueError("follow-up note must reference the same outcome")
        if outcome.advisor_id != followup_note.advisor_id:
            raise ValueError("follow-up note must match the outcome advisor")

        return AdvisorFollowupBundle(
            bundle_id=bundle_id,
            outcome=outcome,
            followup_note=followup_note,
            created_at=created_at or datetime.utcnow(),
        )

    @staticmethod
    def _assert_alignment(
        recommendation: AdvisorRecommendation,
        interpretation: AdvisorInterpretation,
    ) -> None:
        if recommendation.advisor_id != interpretation.advisor_id:
            raise ValueError("recommendation and interpretation advisor mismatch")
        if interpretation.interpretation_id not in recommendation.source_interpretation_refs:
            raise ValueError("recommendation must reference the source interpretation")

    @staticmethod
    def _derive_action(outcome: AdvisorOutcomeRecord) -> AdvisorFollowupAction:
        if outcome.human_review_required or outcome.status == AdvisorOutcomeStatus.NEEDS_REVIEW:
            return AdvisorFollowupAction.ESCALATE_TO_HUMAN
        if outcome.status in (AdvisorOutcomeStatus.MITIGATED, AdvisorOutcomeStatus.REALIZED):
            return AdvisorFollowupAction.LEARN
        if outcome.status == AdvisorOutcomeStatus.OBSERVED:
            return AdvisorFollowupAction.REVIEW
        return AdvisorFollowupAction.RETAIN

    @staticmethod
    def _build_message(outcome: AdvisorOutcomeRecord, action: AdvisorFollowupAction) -> str:
        return (
            f"Outcome {outcome.status.value} for recommendation {outcome.recommendation_id}: "
            f"{outcome.outcome_summary}. Follow-up action: {action.value}."
        )
