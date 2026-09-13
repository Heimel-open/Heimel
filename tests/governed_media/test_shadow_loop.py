from datetime import date, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from valo_platform.governed_media.models import (
    ApprovalState,
    CandidateType,
    ChannelVariant,
    DigestRef,
    FounderTimeRecord,
    HandlingMode,
    MediaChannel,
    sha256_text,
)
from valo_platform.governed_media.shadow_loop import (
    OpportunitySignal,
    build_daily_linkedin_shadow_queue,
    build_seven_day_shadow_report,
)


def ref(name: str) -> DigestRef:
    return DigestRef(ref=name, digest_sha256=sha256_text(name))


def variant(index: int) -> ChannelVariant:
    content = f"Evidence-bound LinkedIn draft {index}"
    return ChannelVariant(
        variant_id=f"variant-{index}",
        canonical_asset_id=f"asset-{index}",
        campaign_id="campaign-1",
        channel=MediaChannel.LINKEDIN,
        account_identity="founder-profile",
        rendered_content=content,
        rendered_content_digest=sha256_text(content),
        source_refs=[ref(f"source-{index}")],
        ai_production_disclosure="AI-assisted draft; founder approval required",
        platform_constraints_checked=False,
        risk_class="material",
        handling_mode=HandlingMode.BATCH_APPROVAL,
        approval_state=ApprovalState.PENDING,
    )


def signal(index: int, candidate_type: CandidateType, theme: str, score: float = 0.9, **kwargs):
    return OpportunitySignal(
        signal_id=f"signal-{index}",
        observed_at=datetime(2026, 7, 28, 8 + (index // 60), index % 60, tzinfo=timezone.utc),
        candidate_type=candidate_type,
        theme_key=theme,
        source_asset_id=f"asset-{index}",
        variant=None if candidate_type == CandidateType.PRIVATE_MESSAGE else variant(index),
        audience_intent_id="enterprise-governance",
        why_now="New verified project work",
        relationship_objective="Create a qualified technical conversation",
        strategic_relevance=score,
        evidence_strength=score,
        novelty=score,
        timeliness=score,
        audience_fit=score,
        relationship_value=score,
        authority_risk=kwargs.pop("authority_risk", 0.05),
        founder_effort_minutes=kwargs.pop("founder_effort_minutes", 5),
        **kwargs,
    )


def test_queue_blocks_private_messages_and_caps_volume() -> None:
    signals = [signal(i, CandidateType.POST, f"post-{i}") for i in range(5)]
    signals += [signal(10 + i, CandidateType.COMMENT, f"comment-{i}") for i in range(7)]
    signals.append(signal(99, CandidateType.PRIVATE_MESSAGE, "dm"))

    queue = build_daily_linkedin_shadow_queue(date(2026, 7, 28), signals)

    assert len(queue.post_candidates) == 3
    assert len(queue.comment_candidates) == 5
    reasons = {entry.reason for entry in queue.suppressed}
    assert "post_daily_limit" in reasons
    assert "comment_daily_limit" in reasons
    assert "private_message_blocked" in reasons
    assert queue.publication_enabled is False


def test_queue_suppresses_duplicate_theme_deterministically() -> None:
    lower = signal(1, CandidateType.POST, "execution-boundary", score=0.7)
    higher = signal(2, CandidateType.POST, "execution-boundary", score=0.95)

    queue = build_daily_linkedin_shadow_queue(date(2026, 7, 28), [lower, higher])

    assert [item.source_signal_ids for item in queue.post_candidates] == [["signal-2"]]
    assert any(
        item.signal_id == "signal-1" and item.reason == "duplicate_lower_rank"
        for item in queue.suppressed
    )


def test_named_relationship_comment_routes_to_direct_human() -> None:
    queue = build_daily_linkedin_shadow_queue(
        date(2026, 7, 28),
        [signal(1, CandidateType.COMMENT, "authority", named_relationship=True)],
    )
    assert queue.comment_candidates[0].handling_mode == HandlingMode.DIRECT_HUMAN


def test_seven_day_shadow_report_uses_observed_time_only() -> None:
    start = date(2026, 7, 28)
    queues = []
    times = []
    for offset in range(7):
        day = start + timedelta(days=offset)
        queues.append(
            build_daily_linkedin_shadow_queue(
                day,
                [signal(offset, CandidateType.POST, f"t-{offset}")],
            )
        )
        times.append(
            FounderTimeRecord(
                record_date=day,
                channel=MediaChannel.LINKEDIN,
                baseline_manual_minutes=150,
                review_minutes=15,
                relationship_minutes=15,
                automated_production_minutes_avoided=120,
            )
        )

    report = build_seven_day_shadow_report(queues, times)

    assert report.baseline_minutes == 1050
    assert report.observed_founder_minutes == 210
    assert report.automated_minutes_avoided == 840
    assert report.observed_automation_rate == 0.8
    assert report.meets_eighty_percent_target is True
    assert report.publication_enabled is False


def test_report_requires_exactly_seven_days() -> None:
    day = date(2026, 7, 28)
    queue = build_daily_linkedin_shadow_queue(day, [signal(1, CandidateType.POST, "one")])
    time = FounderTimeRecord(
        record_date=day,
        channel=MediaChannel.LINKEDIN,
        baseline_manual_minutes=150,
        review_minutes=15,
        relationship_minutes=15,
        automated_production_minutes_avoided=120,
    )
    with pytest.raises((ValidationError, ValueError), match="seven distinct"):
        build_seven_day_shadow_report([queue], [time])


def test_rank_order_is_stable_for_equal_scores() -> None:
    first = signal(2, CandidateType.POST, "b", score=0.9, founder_effort_minutes=5)
    second = signal(1, CandidateType.POST, "a", score=0.9, founder_effort_minutes=5)
    queue = build_daily_linkedin_shadow_queue(date(2026, 7, 28), [first, second])
    assert [item.source_signal_ids[0] for item in queue.post_candidates] == ["signal-1", "signal-2"]
