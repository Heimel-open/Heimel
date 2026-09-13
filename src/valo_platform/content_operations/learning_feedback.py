"""Authority-free learning feedback for governed publication.

Observed performance becomes typed evidence for future proposals. The learning
engine can create recommendations with full lineage, but it cannot issue
clearance, alter mandate or policy, change execution bindings, or publish.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Sequence

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class PublicationMetricName(str, Enum):
    VIEWS = "views"
    WATCH_TIME = "watch_time"
    RETENTION = "retention"
    CLICK_THROUGH_RATE = "click_through_rate"
    ENGAGEMENT = "engagement"
    CONVERSIONS = "conversions"


class PerformanceMetric(BaseModel):
    """One provenance-bound performance observation."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    metric_id: str = Field(min_length=1)
    name: PublicationMetricName
    value: float
    unit: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    definition_ref: str = Field(min_length=1)
    window_start: datetime
    window_end: datetime
    observed_at: datetime
    transformation_refs: tuple[str, ...] = ()

    @field_validator("window_start", "window_end", "observed_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("metric times must be timezone-aware")
        return value

    @field_validator("transformation_refs", mode="before")
    @classmethod
    def normalize_transformations(cls, value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        values = [value] if isinstance(value, str) else list(value)
        normalized = {item.strip() for item in values if isinstance(item, str) and item.strip()}
        if len(normalized) != len(values):
            raise ValueError("transformation_refs must contain non-empty strings")
        return tuple(sorted(normalized))

    @model_validator(mode="after")
    def validate_window(self) -> "PerformanceMetric":
        if self.window_end <= self.window_start:
            raise ValueError("metric window_end must be after window_start")
        if self.observed_at < self.window_end:
            raise ValueError("metric observed_at cannot precede window_end")
        return self


class PublicationOutcomeEvidence(BaseModel):
    """Execution outcome linked back to the exact cleared publication action."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    outcome_id: str = Field(min_length=1)
    execution_receipt_ref: str = Field(min_length=1)
    execution_id: str = Field(min_length=1)
    action_case_hash: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    publication_payload_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    provider_reference: str = Field(min_length=1)
    metrics: tuple[PerformanceMetric, ...] = Field(min_length=1)
    observed_at: datetime

    @field_validator("observed_at")
    @classmethod
    def require_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("outcome observed_at must be timezone-aware")
        return value

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    def digest(self) -> str:
        return _digest(self.canonical_payload())


class PublicationRecommendationKind(str, Enum):
    TOPIC = "topic"
    HOOK = "hook"
    DURATION = "duration"
    FORMAT = "format"
    POSTING_TIME = "posting_time"
    POLICY_CHANGE_PROPOSAL = "policy_change_proposal"


RecommendationValue = str | int | float | bool


class RecommendationParameter(BaseModel):
    """Immutable non-executable recommendation parameter."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    key: str = Field(min_length=1)
    value: RecommendationValue


class PublicationRecommendation(BaseModel):
    """Lineage-bound proposal for later governed consideration."""

    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)

    recommendation_id: str = Field(min_length=1)
    kind: PublicationRecommendationKind
    parameters: tuple[RecommendationParameter, ...] = Field(min_length=1)
    rationale: str = Field(min_length=1)
    source_outcome_refs: tuple[str, ...] = Field(min_length=1)
    source_execution_receipt_refs: tuple[str, ...] = Field(min_length=1)
    source_metric_refs: tuple[str, ...] = Field(min_length=1)
    lineage_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    created_at: datetime


class PublicationLearningError(ValueError):
    pass


class PublicationLearningEngine:
    """Convert outcome evidence into recommendations without execution authority."""

    _PROTECTED_KEYS = {
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
    }

    def recommend(
        self,
        *,
        recommendation_id: str,
        kind: PublicationRecommendationKind,
        parameters: Sequence[RecommendationParameter],
        rationale: str,
        outcomes: Sequence[PublicationOutcomeEvidence],
        created_at: datetime | None = None,
    ) -> PublicationRecommendation:
        if not outcomes:
            raise PublicationLearningError("recommendation requires outcome evidence")
        if not parameters:
            raise PublicationLearningError("recommendation requires parameters")
        if not rationale.strip():
            raise PublicationLearningError("recommendation requires rationale")

        normalized_parameters = tuple(sorted(parameters, key=lambda item: item.key))
        protected = sorted(
            parameter.key for parameter in normalized_parameters if parameter.key in self._PROTECTED_KEYS
        )
        if protected:
            raise PublicationLearningError(
                "learning cannot propose protected execution or authority fields: "
                + ", ".join(protected)
            )

        created_at = _as_utc(created_at or datetime.now(timezone.utc))
        ordered_outcomes = tuple(sorted(outcomes, key=lambda item: item.outcome_id))
        source_outcome_refs = tuple(item.outcome_id for item in ordered_outcomes)
        source_execution_receipt_refs = tuple(
            sorted({item.execution_receipt_ref for item in ordered_outcomes})
        )
        source_metric_refs = tuple(
            sorted({metric.metric_id for item in ordered_outcomes for metric in item.metrics})
        )
        lineage_payload = {
            "recommendation_id": recommendation_id,
            "kind": kind.value,
            "parameters": [item.model_dump(mode="json") for item in normalized_parameters],
            "rationale": rationale.strip(),
            "source_outcomes": [item.canonical_payload() for item in ordered_outcomes],
            "created_at": created_at.isoformat(),
        }
        return PublicationRecommendation(
            recommendation_id=recommendation_id,
            kind=kind,
            parameters=normalized_parameters,
            rationale=rationale.strip(),
            source_outcome_refs=source_outcome_refs,
            source_execution_receipt_refs=source_execution_receipt_refs,
            source_metric_refs=source_metric_refs,
            lineage_digest=_digest(lineage_payload),
            created_at=created_at,
        )


def _digest(payload: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(rfc8785.dumps(payload)).hexdigest()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise PublicationLearningError("time must be timezone-aware")
    return value.astimezone(timezone.utc)
