"""Deterministic, seeded canary tests proving no cross-audience leakage (#674)."""

from datetime import datetime, timezone

import pytest

from src.valo_platform.company_voice.audience_context import AudienceContextResolver
from src.valo_platform.company_voice.models import (
    AudienceContext,
    AudienceType,
    CanonicalOrganizationRecord,
    ChannelType,
    SensitivityLevel,
    VerifiedEvent,
)
from src.valo_platform.time_window_enforcer import TimeWindow


def _customer_record() -> CanonicalOrganizationRecord:
    """A canonical record containing a CUSTOMER-specific (CONFIDENTIAL) canary."""
    customer_canary = VerifiedEvent(
        event_id="cust-canary",
        topic="customer_private",
        summary="CANARY: customer X balance",
        evidence_refs=("evt-cust",),
        sensitivity=SensitivityLevel.CONFIDENTIAL,
    )
    public_item = VerifiedEvent(
        event_id="pub-1",
        topic="product_news",
        summary="Public product update",
        evidence_refs=("evt-pub",),
        sensitivity=SensitivityLevel.PUBLIC,
    )
    return CanonicalOrganizationRecord(
        record_id="rec-cust",
        organization_id="org-1",
        period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 1, 31, tzinfo=timezone.utc),
        events=(customer_canary, public_item),
        evidence_refs=("evt-cust", "evt-pub"),
    )


def _audience(aud_type: AudienceType, ceiling: SensitivityLevel, perms=()) -> AudienceContext:
    return AudienceContext(
        audience_id=f"aud-{aud_type.value}",
        audience_type=aud_type,
        relationship=aud_type.value,
        jurisdiction="NO",
        authorized_topics=(),
        prohibited_topics=(),
        sensitivity_ceiling=ceiling,
        disclosure_profile="std",
        advice_permissions=tuple(perms),
        valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


# Seeded canary topic that must NEVER appear outside the customer audience.
CANARY_TOPIC = "customer_private"


def test_customer_canary_does_not_leak_to_public():
    rec = _customer_record()
    resolver = AudienceContextResolver(
        {"public": _audience(AudienceType.PUBLIC, SensitivityLevel.PUBLIC)}
    )
    proj = resolver.resolve(rec, resolver.get_audience("public"))
    topics = {getattr(i, "topic", "") for i in proj.included_items}
    assert CANARY_TOPIC not in topics
    assert "product_news" in topics  # public item survives


def test_customer_canary_does_not_leak_to_investor():
    rec = _customer_record()
    resolver = AudienceContextResolver(
        {"investor": _audience(AudienceType.INVESTOR, SensitivityLevel.INTERNAL)}
    )
    proj = resolver.resolve(rec, resolver.get_audience("investor"))
    topics = {getattr(i, "topic", "") for i in proj.included_items}
    assert CANARY_TOPIC not in topics


def test_customer_canary_does_not_leak_to_employee():
    rec = _customer_record()
    resolver = AudienceContextResolver(
        {"employee": _audience(AudienceType.EMPLOYEE, SensitivityLevel.CONFIDENTIAL)}
    )
    proj = resolver.resolve(rec, resolver.get_audience("employee"))
    topics = {getattr(i, "topic", "") for i in proj.included_items}
    assert CANARY_TOPIC not in topics


def test_public_channel_rejects_non_public_records():
    restricted = VerifiedEvent(
        event_id="r1",
        topic="internal_only",
        summary="Internal matter",
        evidence_refs=("e",),
        sensitivity=SensitivityLevel.INTERNAL,
    )
    rec = CanonicalOrganizationRecord(
        record_id="rec-2",
        organization_id="org-1",
        period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 1, 31, tzinfo=timezone.utc),
        events=(restricted,),
        evidence_refs=("e",),
    )
    resolver = AudienceContextResolver(
        {"public": _audience(AudienceType.PUBLIC, SensitivityLevel.PUBLIC)}
    )
    proj = resolver.resolve(rec, resolver.get_audience("public"))
    assert len(proj.included_items) == 0


def test_investor_channel_excludes_restricted_mnpi():
    mnpi = VerifiedEvent(
        event_id="m1",
        topic="earnings_leak",
        summary="Unannounced earnings",
        evidence_refs=("e",),
        sensitivity=SensitivityLevel.RESTRICTED,
    )
    rec = CanonicalOrganizationRecord(
        record_id="rec-3",
        organization_id="org-1",
        period_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
        period_end=datetime(2026, 1, 31, tzinfo=timezone.utc),
        events=(mnpi,),
        evidence_refs=("e",),
    )
    # Investor WITHOUT mnpi permission -> excluded.
    resolver = AudienceContextResolver(
        {"investor": _audience(AudienceType.INVESTOR, SensitivityLevel.INTERNAL)}
    )
    proj = resolver.resolve(rec, resolver.get_audience("investor"))
    assert len(proj.included_items) == 0


def test_resolution_is_deterministic():
    rec = _customer_record()
    resolver = AudienceContextResolver(
        {"public": _audience(AudienceType.PUBLIC, SensitivityLevel.PUBLIC)}
    )
    a = resolver.resolve(rec, resolver.get_audience("public"))
    b = resolver.resolve(rec, resolver.get_audience("public"))
    assert [getattr(i, "event_id", "") for i in a.included_items] == [
        getattr(i, "event_id", "") for i in b.included_items
    ]
