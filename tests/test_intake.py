from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from valo_platform.governed_media.intake import (
    ApprovedLinkedInSignal,
    PublicUseApproval,
    SignalSourceType,
    intake_approved_linkedin_signals,
)
from valo_platform.governed_media.linkedin_adapter import LinkedInDraftRequest
from valo_platform.governed_media.models import (
    CandidateType,
    Confidentiality,
    DigestRef,
    MediaChannel,
    sha256_text,
)


def ref(name: str) -> DigestRef:
    return DigestRef(ref=name, digest_sha256=sha256_text(name))


def record(**overrides) -> ApprovedLinkedInSignal:
    observed = datetime(2026, 7, 28, 8, 0, tzinfo=timezone.utc)
    source = ref("repo:commit:abc")
    values = {
        "source_type": SignalSourceType.REPOSITORY_CHANGE,
        "source_artifact_ref": source,
        "confidentiality": Confidentiality.PUBLIC,
        "public_use_approval": PublicUseApproval(
            approval_ref=ref("approval:1"),
            approved_by="founder",
            approved_at=observed - timedelta(minutes=10),
            allowed_channels=[MediaChannel.LINKEDIN],
        ),
        "draft": LinkedInDraftRequest(
            signal_id="signal-1",
            observed_at=observed,
            candidate_type=CandidateType.POST,
            theme_key="execution-boundary",
            canonical_asset_id="asset-1",
            campaign_id="campaign-1",
            account_identity="founder-profile",
            audience_intent_id="enterprise-governance",
            rendered_content="Technical capability is not business authority.",
            source_refs=[source],
            ai_production_disclosure="AI-assisted draft; founder approval required",
            why_now="New approved repository change",
            relationship_objective="Create a qualified architecture discussion",
            risk_class="material",
            strategic_relevance=0.9,
            evidence_strength=0.9,
            novelty=0.8,
            timeliness=0.8,
            audience_fit=0.9,
            relationship_value=0.9,
            authority_risk=0.1,
            founder_effort_minutes=5,
        ),
    }
    values.update(overrides)
    return ApprovedLinkedInSignal(**values)


def test_approved_public_signal_enters_intake() -> None:
    signals = intake_approved_linkedin_signals([record()])
    assert len(signals) == 1
    assert signals[0].signal_id == "signal-1"
    assert signals[0].variant is not None
    assert signals[0].variant.source_refs[0].ref == "repo:commit:abc"


def test_non_public_source_fails_closed() -> None:
    with pytest.raises(ValidationError, match="explicitly public"):
        record(confidentiality=Confidentiality.INTERNAL)


def test_revoked_approval_fails_closed() -> None:
    item = record()
    revoked = item.public_use_approval.model_copy(update={"revoked": True})
    with pytest.raises(ValidationError, match="revoked"):
        record(public_use_approval=revoked)


def test_exact_source_binding_is_required() -> None:
    item = record()
    mismatched = item.draft.model_copy(update={"source_refs": [ref("repo:commit:other")]})
    with pytest.raises(ValidationError, match="exact approved source"):
        record(draft=mismatched)


def test_duplicate_approved_signal_id_is_rejected() -> None:
    with pytest.raises(ValueError, match="duplicate approved signal ID"):
        intake_approved_linkedin_signals([record(), record()])
