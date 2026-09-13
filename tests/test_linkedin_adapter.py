from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from valo_platform.governed_media.linkedin_adapter import (
    LinkedInDraftRequest,
    build_linkedin_opportunity_signal,
)
from valo_platform.governed_media.models import CandidateType, DigestRef, HandlingMode, sha256_text


def request(**overrides):
    values = {
        "signal_id": "signal-1",
        "observed_at": datetime(2026, 7, 28, 8, 0, tzinfo=timezone.utc),
        "candidate_type": CandidateType.POST,
        "theme_key": "execution-boundary",
        "canonical_asset_id": "asset-1",
        "campaign_id": "campaign-1",
        "account_identity": "founder-profile",
        "audience_intent_id": "enterprise-governance",
        "rendered_content": "Technical capability is not business authority.",
        "source_refs": [DigestRef(ref="source-1", digest_sha256=sha256_text("source-1"))],
        "ai_production_disclosure": "AI-assisted draft; founder approval required",
        "why_now": "New verified implementation",
        "relationship_objective": "Create a qualified architecture discussion",
        "risk_class": "material",
        "strategic_relevance": 0.9,
        "evidence_strength": 0.9,
        "novelty": 0.8,
        "timeliness": 0.8,
        "audience_fit": 0.9,
        "relationship_value": 0.9,
        "authority_risk": 0.1,
        "founder_effort_minutes": 5,
    }
    values.update(overrides)
    return LinkedInDraftRequest(**values)


def test_adapter_binds_exact_content_and_sources() -> None:
    signal = build_linkedin_opportunity_signal(request())
    assert signal.variant is not None
    assert signal.variant.rendered_content_digest == sha256_text(signal.variant.rendered_content)
    assert signal.variant.source_refs[0].ref == "source-1"
    assert signal.variant.approval_state.value == "pending"


def test_named_relationship_is_direct_human() -> None:
    signal = build_linkedin_opportunity_signal(
        request(candidate_type=CandidateType.COMMENT, named_relationship=True)
    )
    assert signal.variant is not None
    assert signal.variant.handling_mode == HandlingMode.DIRECT_HUMAN


def test_private_message_request_fails_closed() -> None:
    with pytest.raises(ValidationError, match="private-message generation"):
        request(candidate_type=CandidateType.PRIVATE_MESSAGE)
