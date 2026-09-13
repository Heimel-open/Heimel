"""VALO Company Voice — activation gate (issue #674).

Implements ONLY the activation contract and the guard that prevents any
generation without explicit, non-revoked, organization-enabled activation.

Design rules (issue #674 — "non-negotiable boundaries"):
  - disabled by default. The feature must never be silently enabled.
  - no generation without explicit organization + audience activation.
  - pause and revoke must immediately stop generation.
  - the guard fails CLOSED: any state not explicitly permitted raises.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CompanyVoiceActivationState(Enum):
    """Activation lifecycle. Only EXPLICITLY_ENABLED permits generation."""

    DISABLED = "disabled"          # default — never generates
    ENABLED = "enabled"            # organization opted in
    PAUSED = "paused"              # temporarily halted, must not generate
    REVOKED = "revoked"            # permanently stopped, must not generate


# States that permit generation. Everything else fails closed.
_GENERATION_ALLOWED_STATES = frozenset({CompanyVoiceActivationState.ENABLED})


class CompanyVoiceGenerationError(RuntimeError):
    """Raised when generation is attempted without admissible activation."""


@dataclass
class CompanyVoicePreferences:
    """Per-organization feature preferences.

    Disabled by default. Every flag defaults to the safe (off) position so the
    feature cannot be turned on implicitly.
    """

    organization_id: str
    state: CompanyVoiceActivationState = CompanyVoiceActivationState.DISABLED
    enabled_channels: tuple[str, ...] = field(default_factory=tuple)
    consent_revoked: bool = False

    def is_generation_allowed(self) -> bool:
        """True only when enabled, not revoked, and not paused."""
        return (
            self.state in _GENERATION_ALLOWED_STATES
            and not self.consent_revoked
        )


# Process-wide registry of organization preferences (disabled by default).
_preferences_registry: dict[str, CompanyVoicePreferences] = {}


def get_preferences(organization_id: str) -> CompanyVoicePreferences:
    """Return existing preferences or a fresh DISABLED default (never enabled)."""
    prefs = _preferences_registry.get(organization_id)
    if prefs is None:
        prefs = CompanyVoicePreferences(organization_id=organization_id)
        _preferences_registry[organization_id] = prefs
    return prefs


def register_preferences(prefs: CompanyVoicePreferences) -> None:
    """Store/override preferences for an organization (must be set explicitly)."""
    _preferences_registry[prefs.organization_id] = prefs


def require_generation_allowed(organization_id: str) -> CompanyVoicePreferences:
    """Guard every generation attempt.

    Raises CompanyVoiceGenerationError unless the organization is explicitly
    enabled and consent is not revoked. Used by later phases (script/audio
    providers, delivery) before producing any episode, script or audio.
    """
    prefs = get_preferences(organization_id)
    if not prefs.is_generation_allowed():
        raise CompanyVoiceGenerationError(
            f"Company Voice generation not allowed for organization "
            f"{organization_id!r} (state={prefs.state.value}, "
            f"consent_revoked={prefs.consent_revoked}). Feature is disabled by default."
        )
    return prefs
