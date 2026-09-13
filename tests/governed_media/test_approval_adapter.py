from datetime import date, datetime, timezone
from types import SimpleNamespace

from valo_platform.governed_media.approval_adapter import enqueue_daily_shadow_queue
from valo_platform.governed_media.models import (
    ApprovalState,
    CandidateType,
    ChannelVariant,
    DigestRef,
    HandlingMode,
    MediaChannel,
    sha256_text,
)
from valo_platform.governed_media.shadow_loop import (
    OpportunitySignal,
    build_daily_linkedin_shadow_queue,
)


class FakeQueue:
    def __init__(self) -> None:
        self.calls = []

    def enqueue(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(approval_id=f"approval-{len(self.calls)}")


def signal(
    index: int,
    candidate_type: CandidateType,
    theme: str,
    *,
    named_relationship: bool = False,
) -> OpportunitySignal:
    content = f"Evidence-bound LinkedIn draft {index}"
    variant = ChannelVariant(
        variant_id=f"variant-{index}",
        canonical_asset_id=f"asset-{index}",
        campaign_id="campaign-1",
        channel=MediaChannel.LINKEDIN,
        account_identity="founder-profile",
        rendered_content=content,
        rendered_content_digest=sha256_text(content),
        source_refs=[
            DigestRef(
                ref=f"source-{index}",
                digest_sha256=sha256_text(f"source-{index}"),
            )
        ],
        ai_production_disclosure="AI-assisted draft; founder approval required",
        platform_constraints_checked=False,
        risk_class="material",
        handling_mode=HandlingMode.BATCH_APPROVAL,
        approval_state=ApprovalState.PENDING,
    )
    return OpportunitySignal(
        signal_id=f"signal-{index}",
        observed_at=datetime(2026, 7, 28, 8, index, tzinfo=timezone.utc),
        candidate_type=candidate_type,
        theme_key=theme,
        source_asset_id=f"asset-{index}",
        variant=variant,
        audience_intent_id="enterprise-governance",
        why_now="New verified project work",
        relationship_objective="Create a qualified technical conversation",
        strategic_relevance=0.9,
        evidence_strength=0.9,
        novelty=0.9,
        timeliness=0.9,
        audience_fit=0.9,
        relationship_value=0.9,
        authority_risk=0.05,
        founder_effort_minutes=5,
        named_relationship=named_relationship,
    )


def test_daily_queue_maps_to_existing_approval_contract_without_authority() -> None:
    daily = build_daily_linkedin_shadow_queue(
        date(2026, 7, 28),
        [
            signal(1, CandidateType.POST, "post"),
            signal(2, CandidateType.COMMENT, "comment", named_relationship=True),
        ],
    )
    queue = FakeQueue()

    bindings = enqueue_daily_shadow_queue(daily, queue, actor_id="founder", tenant_id="reht")

    assert len(bindings) == 2
    assert all(binding.publication_authority_granted is False for binding in bindings)
    assert queue.calls[0]["action_type"] == "governed_media_post_review"
    assert queue.calls[0]["decision"] == "defer"
    assert queue.calls[0]["connector"] is None
    assert queue.calls[1]["risk_tier"] == "L3"
    assert bindings[1].handling_mode == HandlingMode.DIRECT_HUMAN


def test_source_refs_are_forwarded_as_evidence_ids() -> None:
    daily = build_daily_linkedin_shadow_queue(
        date(2026, 7, 28),
        [signal(3, CandidateType.POST, "evidence")],
    )
    queue = FakeQueue()
    enqueue_daily_shadow_queue(daily, queue, actor_id="founder", tenant_id="reht")
    assert queue.calls[0]["evidence_ids"] == ["source-3"]
