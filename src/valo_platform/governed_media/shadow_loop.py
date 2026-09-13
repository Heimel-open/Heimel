"""Deterministic LinkedIn shadow-loop ranking and seven-day reporting."""

from __future__ import annotations

from datetime import date, datetime
from typing import Dict, Iterable, List, Optional, Tuple

from pydantic import Field, model_validator

from .models import (
    CandidateType,
    ChannelVariant,
    FounderTimeRecord,
    HandlingMode,
    MediaChannel,
    PublicationCandidate,
    StrictModel,
)


class OpportunitySignal(StrictModel):
    signal_id: str = Field(min_length=1)
    observed_at: datetime
    candidate_type: CandidateType
    theme_key: str = Field(min_length=1)
    source_asset_id: str = Field(min_length=1)
    variant: Optional[ChannelVariant] = None
    audience_intent_id: str = Field(min_length=1)
    why_now: str = Field(min_length=1)
    relationship_objective: str = Field(min_length=1)
    strategic_relevance: float = Field(ge=0.0, le=1.0)
    evidence_strength: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    timeliness: float = Field(ge=0.0, le=1.0)
    audience_fit: float = Field(ge=0.0, le=1.0)
    relationship_value: float = Field(ge=0.0, le=1.0)
    authority_risk: float = Field(ge=0.0, le=1.0)
    founder_effort_minutes: int = Field(ge=0)
    named_relationship: bool = False
    sensitive: bool = False


class SuppressedSignal(StrictModel):
    signal_id: str
    reason: str


class DailyShadowQueue(StrictModel):
    queue_date: date
    post_candidates: List[PublicationCandidate] = Field(default_factory=list, max_length=3)
    comment_candidates: List[PublicationCandidate] = Field(default_factory=list, max_length=5)
    suppressed: List[SuppressedSignal] = Field(default_factory=list)
    publication_enabled: bool = False

    @model_validator(mode="after")
    def shadow_mode_cannot_publish(self) -> "DailyShadowQueue":
        if self.publication_enabled:
            raise ValueError("shadow queue cannot enable publication")
        return self


class ShadowCycleReport(StrictModel):
    start_date: date
    end_date: date
    daily_queues: List[DailyShadowQueue]
    time_records: List[FounderTimeRecord]
    total_post_candidates: int = Field(ge=0)
    total_comment_candidates: int = Field(ge=0)
    total_suppressed: int = Field(ge=0)
    baseline_minutes: int = Field(ge=0)
    observed_founder_minutes: int = Field(ge=0)
    automated_minutes_avoided: int = Field(ge=0)
    observed_automation_rate: float = Field(ge=0.0, le=1.0)
    meets_eighty_percent_target: bool
    publication_enabled: bool = False

    @model_validator(mode="after")
    def validate_seven_day_cycle(self) -> "ShadowCycleReport":
        queue_dates = {queue.queue_date for queue in self.daily_queues}
        time_dates = {record.record_date for record in self.time_records}
        if len(self.daily_queues) != 7 or len(queue_dates) != 7:
            raise ValueError("shadow cycle requires exactly seven distinct daily queues")
        if len(self.time_records) != 7 or len(time_dates) != 7:
            raise ValueError("shadow cycle requires exactly seven distinct time records")
        if queue_dates != time_dates:
            raise ValueError("queue dates and time-record dates must match")
        if self.start_date != min(queue_dates) or self.end_date != max(queue_dates):
            raise ValueError("cycle date range must match queue dates")
        if self.publication_enabled:
            raise ValueError("shadow cycle cannot enable publication")
        return self


DEFAULT_WEIGHTS: Dict[str, float] = {
    "strategic_relevance": 0.22,
    "evidence_strength": 0.20,
    "novelty": 0.14,
    "timeliness": 0.12,
    "audience_fit": 0.14,
    "relationship_value": 0.18,
}


def rank_signal(signal: OpportunitySignal) -> float:
    positive = sum(getattr(signal, key) * weight for key, weight in DEFAULT_WEIGHTS.items())
    risk_penalty = signal.authority_risk * 0.20
    effort_penalty = min(signal.founder_effort_minutes / 60.0, 1.0) * 0.08
    return round(max(0.0, min(1.0, positive - risk_penalty - effort_penalty)), 6)


def build_daily_linkedin_shadow_queue(
    queue_date: date,
    signals: Iterable[OpportunitySignal],
    minimum_score: float = 0.35,
) -> DailyShadowQueue:
    eligible: List[Tuple[OpportunitySignal, float]] = []
    suppressed: List[SuppressedSignal] = []

    for signal in signals:
        if signal.candidate_type == CandidateType.PRIVATE_MESSAGE:
            suppressed.append(SuppressedSignal(signal_id=signal.signal_id, reason="private_message_blocked"))
            continue
        if signal.variant is None:
            suppressed.append(SuppressedSignal(signal_id=signal.signal_id, reason="missing_exact_variant"))
            continue
        if signal.variant.channel != MediaChannel.LINKEDIN:
            suppressed.append(SuppressedSignal(signal_id=signal.signal_id, reason="wrong_channel"))
            continue
        score = rank_signal(signal)
        if score < minimum_score:
            suppressed.append(SuppressedSignal(signal_id=signal.signal_id, reason="below_value_threshold"))
            continue
        eligible.append((signal, score))

    deduplicated: Dict[Tuple[CandidateType, str], Tuple[OpportunitySignal, float]] = {}
    for signal, score in eligible:
        key = (signal.candidate_type, signal.theme_key.lower())
        current = deduplicated.get(key)
        if current is None or _sort_key(signal, score) < _sort_key(current[0], current[1]):
            if current is not None:
                suppressed.append(
                    SuppressedSignal(signal_id=current[0].signal_id, reason="duplicate_lower_rank")
                )
            deduplicated[key] = (signal, score)
        else:
            suppressed.append(SuppressedSignal(signal_id=signal.signal_id, reason="duplicate_lower_rank"))

    posts: List[PublicationCandidate] = []
    comments: List[PublicationCandidate] = []
    ranked = sorted(deduplicated.values(), key=lambda item: _sort_key(item[0], item[1]))

    for signal, score in ranked:
        handling_mode = (
            HandlingMode.DIRECT_HUMAN
            if signal.named_relationship or signal.sensitive
            else HandlingMode.BATCH_APPROVAL
        )
        candidate = PublicationCandidate(
            candidate_id=f"candidate:{queue_date.isoformat()}:{signal.signal_id}",
            candidate_type=signal.candidate_type,
            variant=signal.variant,
            audience_intent_id=signal.audience_intent_id,
            why_now=signal.why_now,
            relationship_objective=signal.relationship_objective,
            strategic_relevance=signal.strategic_relevance,
            evidence_strength=signal.evidence_strength,
            novelty=signal.novelty,
            timeliness=signal.timeliness,
            audience_fit=signal.audience_fit,
            relationship_value=signal.relationship_value,
            authority_risk=signal.authority_risk,
            founder_effort_minutes=signal.founder_effort_minutes,
            ranking_score=score,
            handling_mode=handling_mode,
            source_signal_ids=[signal.signal_id],
        )
        if signal.candidate_type == CandidateType.POST:
            if len(posts) < 3:
                posts.append(candidate)
            else:
                suppressed.append(SuppressedSignal(signal_id=signal.signal_id, reason="post_daily_limit"))
        elif signal.candidate_type == CandidateType.COMMENT:
            if len(comments) < 5:
                comments.append(candidate)
            else:
                suppressed.append(
                    SuppressedSignal(signal_id=signal.signal_id, reason="comment_daily_limit")
                )

    return DailyShadowQueue(
        queue_date=queue_date,
        post_candidates=posts,
        comment_candidates=comments,
        suppressed=sorted(suppressed, key=lambda item: (item.reason, item.signal_id)),
        publication_enabled=False,
    )


def build_seven_day_shadow_report(
    daily_queues: List[DailyShadowQueue],
    time_records: List[FounderTimeRecord],
) -> ShadowCycleReport:
    queue_dates = {queue.queue_date for queue in daily_queues}
    if not queue_dates:
        raise ValueError("at least one daily queue is required")

    total_posts = sum(len(queue.post_candidates) for queue in daily_queues)
    total_comments = sum(len(queue.comment_candidates) for queue in daily_queues)
    total_suppressed = sum(len(queue.suppressed) for queue in daily_queues)
    baseline = sum(record.baseline_manual_minutes for record in time_records)
    observed = sum(record.review_minutes + record.relationship_minutes for record in time_records)
    avoided = sum(record.automated_production_minutes_avoided for record in time_records)
    rate = 0.0 if baseline == 0 else round(avoided / baseline, 6)

    return ShadowCycleReport(
        start_date=min(queue_dates),
        end_date=max(queue_dates),
        daily_queues=daily_queues,
        time_records=time_records,
        total_post_candidates=total_posts,
        total_comment_candidates=total_comments,
        total_suppressed=total_suppressed,
        baseline_minutes=baseline,
        observed_founder_minutes=observed,
        automated_minutes_avoided=avoided,
        observed_automation_rate=rate,
        meets_eighty_percent_target=rate >= 0.80,
        publication_enabled=False,
    )


def _sort_key(signal: OpportunitySignal, score: float) -> Tuple[float, int, str]:
    return (-score, signal.founder_effort_minutes, signal.signal_id)


__all__ = [
    "DailyShadowQueue",
    "OpportunitySignal",
    "ShadowCycleReport",
    "SuppressedSignal",
    "build_daily_linkedin_shadow_queue",
    "build_seven_day_shadow_report",
    "rank_signal",
]
