"""Tests: claim classification + regulated-advice boundary (issue #674)."""

from datetime import datetime, timezone

import pytest

from src.valo_platform.company_voice.claims import classify_claim, get_claim_spec
from src.valo_platform.company_voice.models import (
    AudienceContext,
    AudienceType,
    ChannelType,
    ClaimType,
    CommunicationEnvelope,
    SensitivityLevel,
)
from src.valo_platform.time_window_enforcer import TimeWindow


def _audience(perms=(), ceiling=SensitivityLevel.PUBLIC) -> AudienceContext:
    return AudienceContext(
        audience_id="aud-1",
        audience_type=AudienceType.PUBLIC,
        relationship="public",
        jurisdiction="NO",
        authorized_topics=(),
        prohibited_topics=(),
        sensitivity_ceiling=ceiling,
        disclosure_profile="std",
        advice_permissions=tuple(perms),
        valid_from=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _envelope(channel=ChannelType.PUBLIC_PODCAST, ceiling=SensitivityLevel.PUBLIC) -> CommunicationEnvelope:
    return CommunicationEnvelope(
        envelope_id="env-1",
        publisher_id="pub-1",
        purpose_id="purpose-1",
        audience_context_ref="aud-1",
        personal_context_ref=None,
        source_record_ref="rec-1",
        channel_type=channel,
        authorized_topics=(),
        prohibited_topics=(),
        sensitivity_ceiling=ceiling,
        claim_policy_ref="claim-1",
        disclosure_policy_ref="disc-1",
        approval_requirements=(),
        validity_window=TimeWindow(name="always"),
        retention_policy_ref="ret-1",
        correction_policy_ref="corr-1",
    )


def test_verified_fact_requires_evidence():
    assert classify_claim(ClaimType.VERIFIED_FACT, _envelope(), _audience(), has_evidence=True) is True
    assert classify_claim(ClaimType.VERIFIED_FACT, _envelope(), _audience(), has_evidence=False) is False


def test_regulated_advice_blocked_without_authority():
    env = _envelope(ceiling=SensitivityLevel.RESTRICTED)
    # No advice permission and PUBLIC-ceiling audience -> rejected.
    assert classify_claim(ClaimType.REGULATED_ADVICE, env, _audience(), has_evidence=True, has_authority=True) is False
    # With explicit regulated_advice permission AND a ceiling that admits it -> admissible.
    assert classify_claim(
        ClaimType.REGULATED_ADVICE, env,
        _audience(perms=["regulated_advice"], ceiling=SensitivityLevel.RESTRICTED),
        has_evidence=True, has_authority=True
    ) is True


def test_recommendation_blocked_without_guidance_permission():
    env = _envelope()
    assert classify_claim(ClaimType.RECOMMENDATION, env, _audience(), has_authority=False) is False
    assert classify_claim(
        ClaimType.RECOMMENDATION, env, _audience(perms=["guidance"]), has_authority=True
    ) is True


def test_forecast_requires_uncertainty_label_not_blocked_by_default():
    assert classify_claim(ClaimType.FORECAST, _envelope(), _audience(), has_evidence=False) is True


def test_claim_spec_registry_complete():
    for ct in ClaimType:
        assert get_claim_spec(ct) is not None
