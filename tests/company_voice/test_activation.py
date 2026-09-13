"""Tests: Company Voice disabled-by-default activation gate (issue #674)."""

import pytest

from src.valo_platform.company_voice.activation import (
    CompanyVoiceActivationState,
    CompanyVoiceGenerationError,
    CompanyVoicePreferences,
    get_preferences,
    register_preferences,
    require_generation_allowed,
)


def test_default_preferences_disabled():
    prefs = get_preferences("org-default")
    assert prefs.state == CompanyVoiceActivationState.DISABLED
    assert prefs.is_generation_allowed() is False


def test_generation_allowed_only_when_enabled():
    prefs = CompanyVoicePreferences(
        organization_id="org-1", state=CompanyVoiceActivationState.ENABLED
    )
    register_preferences(prefs)
    assert prefs.is_generation_allowed() is True
    assert require_generation_allowed("org-1") is prefs


@pytest.mark.parametrize(
    "state",
    [
        CompanyVoiceActivationState.DISABLED,
        CompanyVoiceActivationState.PAUSED,
        CompanyVoiceActivationState.REVOKED,
    ],
)
def test_guard_fails_closed_for_non_enabled_states(state):
    prefs = CompanyVoicePreferences(organization_id="org-2", state=state)
    register_preferences(prefs)
    with pytest.raises(CompanyVoiceGenerationError):
        require_generation_allowed("org-2")


def test_consent_revocation_stops_generation():
    prefs = CompanyVoicePreferences(
        organization_id="org-3",
        state=CompanyVoiceActivationState.ENABLED,
        consent_revoked=True,
    )
    register_preferences(prefs)
    with pytest.raises(CompanyVoiceGenerationError):
        require_generation_allowed("org-3")
