import pytest

from src.valo_platform.advisor_fabric import (
    AdvisorFollowupAction,
    AdvisorFollowupService,
    AdvisorOutcomeStatus,
    AdvisorRecommendationService,
)
from src.valo_platform.advisor_fabric.followup_service import AdvisorOutcomeRecord
from src.valo_platform.advisor_fabric.schemas import AdvisorInterpretation


def _interpretation() -> AdvisorInterpretation:
    return AdvisorInterpretation(
        interpretation_id="interp-1",
        advisor_id="ciso",
        source_evidence_refs=["evidence-1"],
        stance="exploit pressure is credible",
        confidence=0.91,
    )


def _recommendation(service: AdvisorRecommendationService, interpretation: AdvisorInterpretation):
    return service.recommend(
        recommendation_id="rec-1",
        interpretation=interpretation,
        statement="prioritize remediation",
        rationale="high confidence and clear exposure",
    )


def test_mitigated_outcome_produces_learn_followup() -> None:
    recommendation_service = AdvisorRecommendationService()
    followup_service = AdvisorFollowupService()
    interpretation = _interpretation()
    recommendation = _recommendation(recommendation_service, interpretation)

    outcome = followup_service.record_outcome(
        outcome_id="out-1",
        recommendation=recommendation,
        interpretation=interpretation,
        status=AdvisorOutcomeStatus.MITIGATED,
        outcome_summary="the control reduced exposure before impact",
        evidence_refs=["evidence-1"],
    )
    note = followup_service.followup_note(note_id="note-1", outcome=outcome)

    assert outcome.status == AdvisorOutcomeStatus.MITIGATED
    assert note.action == AdvisorFollowupAction.LEARN
    assert "mitigated" in note.message


def test_realized_outcome_with_human_review_escalates_to_human() -> None:
    recommendation_service = AdvisorRecommendationService()
    followup_service = AdvisorFollowupService()
    interpretation = _interpretation()
    recommendation = _recommendation(recommendation_service, interpretation)

    outcome = followup_service.record_outcome(
        outcome_id="out-2",
        recommendation=recommendation,
        interpretation=interpretation,
        status=AdvisorOutcomeStatus.REALIZED,
        outcome_summary="the incident materialized and needs postmortem review",
        human_review_required=True,
    )
    note = followup_service.followup_note(note_id="note-2", outcome=outcome)

    assert note.action == AdvisorFollowupAction.ESCALATE_TO_HUMAN
    assert outcome.human_review_required is True


def test_record_outcome_rejects_mismatched_advisor_alignment() -> None:
    recommendation_service = AdvisorRecommendationService()
    followup_service = AdvisorFollowupService()
    interpretation = _interpretation()
    recommendation = _recommendation(recommendation_service, interpretation)
    mismatched_interpretation = AdvisorInterpretation(
        interpretation_id="interp-2",
        advisor_id="cfo",
        source_evidence_refs=["evidence-2"],
        stance="not aligned",
        confidence=0.8,
    )

    with pytest.raises(ValueError, match="advisor mismatch"):
        followup_service.record_outcome(
            outcome_id="out-3",
            recommendation=recommendation,
            interpretation=mismatched_interpretation,
            status=AdvisorOutcomeStatus.OBSERVED,
            outcome_summary="alignment should fail",
        )


def test_outcome_dump_does_not_include_execution_authority_fields() -> None:
    record = AdvisorOutcomeRecord(
        outcome_id="out-4",
        recommendation_id="rec-4",
        advisor_id="ciso",
        status=AdvisorOutcomeStatus.NO_THREAT,
        outcome_summary="no active threat was observed",
    )

    dumped = record.model_dump()

    assert "execution_authority" not in dumped
    assert "permit_id" not in dumped
    assert dumped["authority_boundary"].value == "advisory_only"
