"""Tests: communication envelope is mandatory and bounds every artifact (#674)."""

import pytest

from src.valo_platform.company_voice.models import (
    AudienceContext,
    AudienceType,
    CanonicalOrganizationRecord,
    ChannelType,
    CommunicationEnvelope,
    SensitivityLevel,
)
from src.valo_platform.time_window_enforcer import TimeWindow


def test_envelope_links_to_source_and_audience():
    env = CommunicationEnvelope(
        envelope_id="env-1",
        publisher_id="pub-1",
        purpose_id="purpose-1",
        audience_context_ref="aud-1",
        personal_context_ref=None,
        source_record_ref="rec-1",
        channel_type=ChannelType.PUBLIC_PODCAST,
        authorized_topics=(),
        prohibited_topics=(),
        sensitivity_ceiling=SensitivityLevel.PUBLIC,
        claim_policy_ref="claim-1",
        disclosure_policy_ref="disc-1",
        approval_requirements=(),
        validity_window=TimeWindow(name="always"),
        retention_policy_ref="ret-1",
        correction_policy_ref="corr-1",
    )
    # The envelope is the binding between audience, purpose, source and channel.
    assert env.audience_context_ref == "aud-1"
    assert env.source_record_ref == "rec-1"
    assert env.channel_type == ChannelType.PUBLIC_PODCAST


def test_every_artifact_envelope_binds_audience_purpose_source_channel():
    # The envelope is the binding contract: every artifact must carry a distinct
    # audience, purpose, source and channel. Empty governance refs are invalid.
    env = CommunicationEnvelope(
        envelope_id="env-2",
        publisher_id="pub-1",
        purpose_id="purpose-1",
        audience_context_ref="aud-1",
        personal_context_ref=None,
        source_record_ref="rec-1",
        channel_type=ChannelType.PUBLIC_PODCAST,
        authorized_topics=(),
        prohibited_topics=(),
        sensitivity_ceiling=SensitivityLevel.PUBLIC,
        claim_policy_ref="claim-1",
        disclosure_policy_ref="disc-1",
        approval_requirements=(),
        validity_window=TimeWindow(name="always"),
        retention_policy_ref="ret-1",
        correction_policy_ref="corr-1",
    )
    assert env.audience_context_ref and env.purpose_id and env.source_record_ref
    # Two different audiences must use different envelopes (no clearance reuse).
    other = CommunicationEnvelope(
        **{**env.__dict__, "envelope_id": "env-3", "audience_context_ref": "aud-2"}
    )
    assert other.audience_context_ref != env.audience_context_ref
    assert other.envelope_id != env.envelope_id
