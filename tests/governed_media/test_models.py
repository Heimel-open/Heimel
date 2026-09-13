from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from valo_platform.governed_media.models import (
    ApprovalState,
    CandidateType,
    ChannelVariant,
    ClaimBinding,
    DigestRef,
    FounderTimeRecord,
    HandlingMode,
    MediaChannel,
    PublicationCandidate,
    PublicationDecision,
    sha256_text,
)


def ref(name: str) -> DigestRef:
    return DigestRef(ref=name, digest_sha256=sha256_text(name))


def variant(content: str = "Technical capability is not business authority.") -> ChannelVariant:
    return ChannelVariant(
        variant_id="variant-1",
        canonical_asset_id="asset-1",
        campaign_id="campaign-1",
        channel=MediaChannel.LINKEDIN,
        account_identity="founder-profile",
        rendered_content=content,
        rendered_content_digest=sha256_text(content),
        source_refs=[ref("source-1")],
        claim_bindings=[],
        ai_production_disclosure="AI-assisted draft; founder approval required",
        platform_constraints_checked=False,
        risk_class="material",
        handling_mode=HandlingMode.BATCH_APPROVAL,
        approval_state=ApprovalState.PENDING,
    )


def test_material_claim_requires_evidence() -> None:
    with pytest.raises(ValidationError, match="material claims require"):
        ClaimBinding(claim_id="claim-1", text="A material statement", material=True)


def test_channel_variant_digest_is_exact() -> None:
    with pytest.raises(ValidationError, match="does not match"):
        ChannelVariant(
            variant_id="variant-1",
            canonical_asset_id="asset-1",
            campaign_id="campaign-1",
            channel=MediaChannel.LINKEDIN,
            account_identity="founder-profile",
            rendered_content="content",
            rendered_content_digest="0" * 64,
            source_refs=[ref("source-1")],
            ai_production_disclosure="AI-assisted",
            risk_class="low",
        )


def test_private_message_candidate_is_rejected() -> None:
    with pytest.raises(ValidationError, match="private-message"):
        PublicationCandidate(
            candidate_id="candidate-1",
            candidate_type=CandidateType.PRIVATE_MESSAGE,
            variant=variant(),
            audience_intent_id="audience-1",
            why_now="Relevant now",
            relationship_objective="Open a discussion",
            strategic_relevance=0.9,
            evidence_strength=0.9,
            novelty=0.8,
            timeliness=0.8,
            audience_fit=0.9,
            relationship_value=0.9,
            authority_risk=0.1,
            founder_effort_minutes=5,
            ranking_score=0.8,
            handling_mode=HandlingMode.DIRECT_HUMAN,
            source_signal_ids=["signal-1"],
        )


def test_approval_requires_exact_variant_digest() -> None:
    with pytest.raises(ValidationError, match="exact approved variant digest"):
        PublicationDecision(
            decision_id="decision-1",
            candidate_id="candidate-1",
            state=ApprovalState.APPROVED,
            decided_by="founder",
            decided_at=datetime.now(timezone.utc),
        )


def test_founder_time_record_rejects_synthetic_saving() -> None:
    with pytest.raises(ValidationError, match="baseline minus observed"):
        FounderTimeRecord(
            record_date=date(2026, 7, 28),
            channel=MediaChannel.LINKEDIN,
            baseline_manual_minutes=150,
            review_minutes=15,
            relationship_minutes=15,
            automated_production_minutes_avoided=150,
        )


def test_founder_time_record_calculates_observed_rate() -> None:
    record = FounderTimeRecord(
        record_date=date(2026, 7, 28),
        channel=MediaChannel.LINKEDIN,
        baseline_manual_minutes=150,
        review_minutes=15,
        relationship_minutes=15,
        automated_production_minutes_avoided=120,
    )
    assert record.automation_rate == 0.8


def test_extra_fields_fail_closed() -> None:
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        DigestRef(ref="x", digest_sha256=sha256_text("x"), hidden_authority=True)
