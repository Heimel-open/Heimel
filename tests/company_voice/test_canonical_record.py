"""Tests: CanonicalOrganizationRecord + projection contract (issue #674)."""

import pytest
from datetime import datetime, timezone

from src.valo_platform.company_voice.models import (
    AudienceContext,
    AudienceType,
    CanonicalOrganizationRecord,
    CommunicationEnvelope,
    SensitivityLevel,
    VerifiedEvent,
    compute_source_scope_hash,
)


def _record() -> CanonicalOrganizationRecord:
    ev = VerifiedEvent(
        event_id="e1",
        topic="liquidity",
        summary="Cash position updated",
        evidence_refs=("evt-1",),
        sensitivity=SensitivityLevel.INTERNAL,
    )
    return CanonicalOrganizationRecord(
        record_id="rec-1",
        organization_id="org-1",
        period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 1, 31, tzinfo=timezone.utc),
        events=(ev,),
        evidence_refs=("evt-1",),
    )


def test_record_is_frozen():
    rec = _record()
    with pytest.raises(Exception):
        rec.organization_id = "other"  # type: ignore[misc]


def test_source_scope_hash_is_deterministic():
    h1 = compute_source_scope_hash(("b", "a"))
    h2 = compute_source_scope_hash(("a", "b"))
    assert h1 == h2
    assert len(h1) == 64


def test_envelope_requires_source_reference():
    env = CommunicationEnvelope(
        envelope_id="env-1",
        publisher_id="pub-1",
        purpose_id="purpose-1",
        audience_context_ref="aud-1",
        personal_context_ref=None,
        source_record_ref="rec-1",
        channel_type=__import__("src.valo_platform.company_voice.models", fromlist=["ChannelType"]).ChannelType.PUBLIC_PODCAST,
        authorized_topics=(),
        prohibited_topics=(),
        sensitivity_ceiling=SensitivityLevel.PUBLIC,
        claim_policy_ref="claim-1",
        disclosure_policy_ref="disc-1",
        approval_requirements=(),
        validity_window=__import__("src.valo_platform.time_window_enforcer", fromlist=["TimeWindow"]).TimeWindow(name="always"),
        retention_policy_ref="ret-1",
        correction_policy_ref="corr-1",
    )
    assert env.source_record_ref == "rec-1"


def test_audience_context_is_frozen():
    aud = AudienceContext(
        audience_id="aud-1",
        audience_type=AudienceType.PUBLIC,
        relationship="public",
        jurisdiction="NO",
        authorized_topics=(),
        prohibited_topics=(),
        sensitivity_ceiling=SensitivityLevel.PUBLIC,
        disclosure_profile="public",
        advice_permissions=(),
        valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )
    with pytest.raises(Exception):
        aud.jurisdiction = "SE"  # type: ignore[misc]
