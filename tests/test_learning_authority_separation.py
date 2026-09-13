from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from src.valo_platform.content_operations import (
    PerformanceMetric,
    PublicationLearningEngine,
    PublicationLearningError,
    PublicationMetricName,
    PublicationOutcomeEvidence,
    PublicationRecommendationKind,
    RecommendationParameter,
)


def sha(char: str) -> str:
    return "sha256:" + char * 64


def metric(
    *,
    metric_id: str = "metric-retention-1",
    name: PublicationMetricName = PublicationMetricName.RETENTION,
    value: float = 0.62,
    transformation_refs: tuple[str, ...] = ("transform:normalized-retention:v1",),
) -> PerformanceMetric:
    window_start = datetime(2026, 7, 30, 8, 0, tzinfo=timezone.utc)
    window_end = window_start + timedelta(hours=24)
    return PerformanceMetric(
        metric_id=metric_id,
        name=name,
        value=value,
        unit="ratio",
        source_ref="youtube-analytics:video:abc123",
        definition_ref="metric-definition:retention:v1",
        window_start=window_start,
        window_end=window_end,
        observed_at=window_end + timedelta(minutes=5),
        transformation_refs=transformation_refs,
    )


def outcome(
    *,
    outcome_id: str = "outcome-publication-1",
    metric_value: float = 0.62,
) -> PublicationOutcomeEvidence:
    observed = datetime(2026, 7, 31, 8, 5, tzinfo=timezone.utc)
    return PublicationOutcomeEvidence(
        outcome_id=outcome_id,
        execution_receipt_ref="receipt:publication:1",
        execution_id="execution-publication-1",
        action_case_hash=sha("1"),
        publication_payload_digest=sha("2"),
        provider_reference="youtube:video:abc123",
        metrics=(metric(value=metric_value),),
        observed_at=observed,
    )


def test_performance_metric_requires_provenance_definition_and_valid_window() -> None:
    observed = metric()

    assert observed.source_ref == "youtube-analytics:video:abc123"
    assert observed.definition_ref == "metric-definition:retention:v1"
    assert observed.transformation_refs == ("transform:normalized-retention:v1",)


def test_invalid_metric_windows_fail_closed() -> None:
    start = datetime(2026, 7, 31, 8, 0, tzinfo=timezone.utc)

    with pytest.raises(ValidationError, match="window_end"):
        PerformanceMetric(
            metric_id="metric-1",
            name=PublicationMetricName.VIEWS,
            value=1,
            unit="count",
            source_ref="analytics:1",
            definition_ref="metric-definition:views:v1",
            window_start=start,
            window_end=start,
            observed_at=start,
        )


def test_naive_metric_time_is_rejected() -> None:
    naive = datetime(2026, 7, 31, 8, 0)

    with pytest.raises(ValidationError, match="timezone-aware"):
        PerformanceMetric(
            metric_id="metric-1",
            name=PublicationMetricName.VIEWS,
            value=1,
            unit="count",
            source_ref="analytics:1",
            definition_ref="metric-definition:views:v1",
            window_start=naive,
            window_end=naive + timedelta(hours=1),
            observed_at=naive + timedelta(hours=2),
        )


def test_outcome_digest_binds_execution_action_payload_and_metrics() -> None:
    original = outcome(metric_value=0.62)
    changed = outcome(metric_value=0.63)

    assert original.digest().startswith("sha256:")
    assert original.digest() != changed.digest()
    assert original.action_case_hash == sha("1")
    assert original.publication_payload_digest == sha("2")


def test_learning_creates_lineage_bound_recommendation_only() -> None:
    created_at = datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc)
    evidence = outcome()

    recommendation = PublicationLearningEngine().recommend(
        recommendation_id="recommendation-hook-1",
        kind=PublicationRecommendationKind.HOOK,
        parameters=(
            RecommendationParameter(key="hook_pattern", value="question-first"),
            RecommendationParameter(key="target_duration_seconds", value=31),
        ),
        rationale="Retention was strongest in the first 31 seconds.",
        outcomes=(evidence,),
        created_at=created_at,
    )

    assert recommendation.kind is PublicationRecommendationKind.HOOK
    assert recommendation.source_outcome_refs == (evidence.outcome_id,)
    assert recommendation.source_execution_receipt_refs == (
        evidence.execution_receipt_ref,
    )
    assert recommendation.source_metric_refs == ("metric-retention-1",)
    assert recommendation.lineage_digest.startswith("sha256:")
    assert not hasattr(recommendation, "clearance_id")
    assert not hasattr(recommendation, "execution_request")


def test_recommendation_lineage_is_deterministic_across_input_order() -> None:
    created_at = datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc)
    first_outcome = outcome(outcome_id="outcome-a")
    second_outcome = PublicationOutcomeEvidence(
        outcome_id="outcome-b",
        execution_receipt_ref="receipt:publication:2",
        execution_id="execution-publication-2",
        action_case_hash=sha("3"),
        publication_payload_digest=sha("4"),
        provider_reference="youtube:video:def456",
        metrics=(
            metric(
                metric_id="metric-views-2",
                name=PublicationMetricName.VIEWS,
                value=1400,
                transformation_refs=(),
            ),
        ),
        observed_at=datetime(2026, 7, 31, 8, 5, tzinfo=timezone.utc),
    )
    params = (
        RecommendationParameter(key="posting_hour_utc", value=17),
        RecommendationParameter(key="weekday", value="Thursday"),
    )
    engine = PublicationLearningEngine()

    first = engine.recommend(
        recommendation_id="recommendation-time-1",
        kind=PublicationRecommendationKind.POSTING_TIME,
        parameters=params,
        rationale="Observed retention and view evidence support a later slot.",
        outcomes=(second_outcome, first_outcome),
        created_at=created_at,
    )
    second = engine.recommend(
        recommendation_id="recommendation-time-1",
        kind=PublicationRecommendationKind.POSTING_TIME,
        parameters=tuple(reversed(params)),
        rationale="Observed retention and view evidence support a later slot.",
        outcomes=(first_outcome, second_outcome),
        created_at=created_at,
    )

    assert first.lineage_digest == second.lineage_digest
    assert first.source_outcome_refs == ("outcome-a", "outcome-b")


@pytest.mark.parametrize(
    "protected_key",
    [
        "account_ref",
        "approval_bypass",
        "authority_ref",
        "channel_ref",
        "clearance_id",
        "commit_token",
        "delegated_mandate_ref",
        "execute",
        "execution_request",
        "mandate_ref",
        "privacy_status",
        "publish",
        "publish_now",
    ],
)
def test_learning_cannot_propose_authority_or_execution_fields(
    protected_key: str,
) -> None:
    with pytest.raises(PublicationLearningError, match="protected"):
        PublicationLearningEngine().recommend(
            recommendation_id="recommendation-invalid",
            kind=PublicationRecommendationKind.FORMAT,
            parameters=(RecommendationParameter(key=protected_key, value=True),),
            rationale="Attempted authority mutation.",
            outcomes=(outcome(),),
        )


def test_policy_change_is_a_proposal_not_a_policy_mutation() -> None:
    recommendation = PublicationLearningEngine().recommend(
        recommendation_id="recommendation-policy-1",
        kind=PublicationRecommendationKind.POLICY_CHANGE_PROPOSAL,
        parameters=(
            RecommendationParameter(
                key="change_request_ref",
                value="change-request:publication-window:1",
            ),
            RecommendationParameter(
                key="suggested_max_publications_24h",
                value=5,
            ),
        ),
        rationale="Observed capacity supports submitting a policy change for human review.",
        outcomes=(outcome(),),
        created_at=datetime(2026, 7, 31, 9, 0, tzinfo=timezone.utc),
    )

    assert recommendation.kind is PublicationRecommendationKind.POLICY_CHANGE_PROPOSAL
    assert not hasattr(recommendation, "policy")
    assert not hasattr(recommendation, "apply")


@pytest.mark.parametrize(
    ("parameters", "outcomes", "rationale", "message"),
    [
        ((), (outcome(),), "Valid rationale", "parameters"),
        (
            (RecommendationParameter(key="topic", value="governance"),),
            (),
            "Valid rationale",
            "outcome evidence",
        ),
        (
            (RecommendationParameter(key="topic", value="governance"),),
            (outcome(),),
            " ",
            "rationale",
        ),
    ],
)
def test_incomplete_learning_inputs_fail_closed(
    parameters: tuple[RecommendationParameter, ...],
    outcomes: tuple[PublicationOutcomeEvidence, ...],
    rationale: str,
    message: str,
) -> None:
    with pytest.raises(PublicationLearningError, match=message):
        PublicationLearningEngine().recommend(
            recommendation_id="recommendation-incomplete",
            kind=PublicationRecommendationKind.TOPIC,
            parameters=parameters,
            rationale=rationale,
            outcomes=outcomes,
        )


def test_learning_models_reject_unknown_fields() -> None:
    payload = metric().model_dump(mode="python")
    payload["grant_authority"] = True

    with pytest.raises(ValidationError, match="Extra inputs"):
        PerformanceMetric.model_validate(payload)


def test_learning_engine_has_no_authority_or_execution_methods() -> None:
    engine = PublicationLearningEngine()

    assert not hasattr(engine, "issue_clearance")
    assert not hasattr(engine, "create_commit_token")
    assert not hasattr(engine, "update_policy")
    assert not hasattr(engine, "update_mandate")
    assert not hasattr(engine, "execute")
    assert not hasattr(engine, "publish")
