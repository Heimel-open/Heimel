"""Tests for evidence-bounded AI transition and political risk evaluation."""

from datetime import datetime, timedelta, timezone

import pytest

from vaig.transition_risk import (
    AITransitionRiskEvaluator,
    AssessmentStatus,
    CompositePolicy,
    EvidencePolicy,
    EvidenceSignal,
    TransitionRiskInputError,
)


NOW = datetime(2026, 8, 11, 9, 30, tzinfo=timezone.utc)


def signal(value=0.5, *, confidence=0.9, age_days=1, source="source", digest="digest"):
    return EvidenceSignal(
        value=value,
        source=source,
        provenance_digest=digest,
        observed_at=NOW - timedelta(days=age_days),
        confidence=confidence,
    )


def hitr_signals():
    return {
        "ai_exposure": signal(0.8),
        "adoption_velocity": signal(0.7),
        "role_redesign": signal(0.6),
        "economic_fragility": signal(0.5),
        "human_resistance": signal(0.4),
        "institutional_transition_risk": signal(0.3),
    }


def hitr_policy():
    return CompositePolicy(
        calibrated=True,
        calibration_ref="test-calibration-v1",
        weights={
            "ai_exposure": 0.20,
            "adoption_velocity": 0.20,
            "role_redesign": 0.20,
            "economic_fragility": 0.15,
            "human_resistance": 0.15,
            "institutional_transition_risk": 0.10,
        },
    )


def test_hitr_returns_components_only_without_calibrated_policy():
    result = AITransitionRiskEvaluator().evaluate_hitr(hitr_signals(), as_of=NOW)

    assert result.status == AssessmentStatus.COMPONENTS_ONLY
    assert result.composite_score is None
    assert result.dimensions["ai_exposure"] == 0.8
    assert result.reasons == ("no_calibrated_composite_policy",)


def test_hitr_scores_only_with_explicit_calibration():
    result = AITransitionRiskEvaluator().evaluate_hitr(
        hitr_signals(), as_of=NOW, composite_policy=hitr_policy()
    )

    assert result.status == AssessmentStatus.SCORED
    assert result.composite_score is not None
    assert 0.0 <= result.composite_score <= 1.0
    assert result.calibration_ref == "test-calibration-v1"
    assert result.evidence_confidence == 0.9


def test_missing_dimension_is_unknown_not_zero():
    signals = hitr_signals()
    del signals["adoption_velocity"]

    result = AITransitionRiskEvaluator().evaluate_hitr(
        signals, as_of=NOW, composite_policy=hitr_policy()
    )

    assert result.status == AssessmentStatus.UNKNOWN
    assert result.composite_score is None
    assert "missing:adoption_velocity" in result.reasons


def test_explicit_unknown_dimension_is_unknown():
    signals = hitr_signals()
    signals["role_redesign"] = signal(None)

    result = AITransitionRiskEvaluator().evaluate_hitr(signals, as_of=NOW)

    assert result.status == AssessmentStatus.UNKNOWN
    assert "unknown:role_redesign" in result.reasons


def test_stale_evidence_is_insufficient_and_cannot_score():
    evaluator = AITransitionRiskEvaluator(EvidencePolicy(max_age_days=30))
    signals = hitr_signals()
    signals["economic_fragility"] = signal(0.5, age_days=31)

    result = evaluator.evaluate_hitr(
        signals, as_of=NOW, composite_policy=hitr_policy()
    )

    assert result.status == AssessmentStatus.INSUFFICIENT_EVIDENCE
    assert result.composite_score is None
    assert "stale:economic_fragility" in result.reasons


def test_missing_provenance_and_low_confidence_are_insufficient():
    signals = hitr_signals()
    signals["human_resistance"] = signal(0.4, confidence=0.4, digest="")

    result = AITransitionRiskEvaluator().evaluate_hitr(
        signals, as_of=NOW, composite_policy=hitr_policy()
    )

    assert result.status == AssessmentStatus.INSUFFICIENT_EVIDENCE
    assert "missing_provenance:human_resistance" in result.reasons
    assert "low_confidence:human_resistance" in result.reasons


def test_future_observation_is_insufficient():
    signals = hitr_signals()
    signals["ai_exposure"] = EvidenceSignal(
        value=0.8,
        source="source",
        provenance_digest="digest",
        observed_at=NOW + timedelta(seconds=1),
        confidence=0.9,
    )

    result = AITransitionRiskEvaluator().evaluate_hitr(signals, as_of=NOW)

    assert result.status == AssessmentStatus.INSUFFICIENT_EVIDENCE
    assert "future_observation:ai_exposure" in result.reasons


def test_invalid_signal_range_fails_closed():
    with pytest.raises(TransitionRiskInputError):
        signal(1.01)


def test_uncalibrated_weights_never_create_composite():
    policy = CompositePolicy(
        calibrated=False,
        calibration_ref="",
        weights={name: 1.0 / 6.0 for name in AITransitionRiskEvaluator.HITR_DIMENSIONS},
    )

    result = AITransitionRiskEvaluator().evaluate_hitr(
        hitr_signals(), as_of=NOW, composite_policy=policy
    )

    assert result.status == AssessmentStatus.COMPONENTS_ONLY
    assert result.composite_score is None


def test_bad_calibrated_policy_is_rejected():
    bad = CompositePolicy(
        calibrated=True,
        calibration_ref="claimed-calibration",
        weights={name: 0.1 for name in AITransitionRiskEvaluator.HITR_DIMENSIONS},
    )

    with pytest.raises(TransitionRiskInputError):
        AITransitionRiskEvaluator().evaluate_hitr(
            hitr_signals(), as_of=NOW, composite_policy=bad
        )


def test_prr_requires_scored_hitr():
    evaluator = AITransitionRiskEvaluator()
    hitr = evaluator.evaluate_hitr(hitr_signals(), as_of=NOW)

    result = evaluator.evaluate_prr(
        hitr,
        {
            "geographic_concentration": signal(0.7),
            "political_sensitivity": signal(0.5),
        },
        as_of=NOW,
    )

    assert result.status == AssessmentStatus.COMPONENTS_ONLY
    assert result.composite_score is None
    assert result.reasons == ("hitr_composite_required_for_prr",)


def test_prr_scores_only_from_scored_hitr_and_calibrated_policy():
    evaluator = AITransitionRiskEvaluator()
    hitr = evaluator.evaluate_hitr(
        hitr_signals(), as_of=NOW, composite_policy=hitr_policy()
    )
    prr_policy = CompositePolicy(
        calibrated=True,
        calibration_ref="test-prr-calibration-v1",
        weights={
            "hitr": 0.60,
            "geographic_concentration": 0.25,
            "political_sensitivity": 0.15,
        },
    )

    result = evaluator.evaluate_prr(
        hitr,
        {
            "geographic_concentration": signal(0.7),
            "political_sensitivity": signal(0.5),
        },
        as_of=NOW,
        composite_policy=prr_policy,
    )

    assert result.status == AssessmentStatus.SCORED
    assert result.composite_score is not None
    assert result.calibration_ref == "test-prr-calibration-v1"
    serialized = result.as_dict()
    assert "job_loss" not in serialized
    assert "party" not in serialized
