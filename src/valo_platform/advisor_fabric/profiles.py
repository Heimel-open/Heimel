"""Advisor Fabric role profile registry.

The registry is data-only. It mirrors the legacy Advisor role set so migration
can proceed behind adapters without importing or instantiating Advisor runtime
classes.
"""

from types import MappingProxyType
from typing import Mapping, Tuple

from .schemas import (
    AdvisorMemoryPolicy,
    AdvisorProfile,
    AdvisorRecommendationType,
)

PROFILE_VERSION = "2026-07-17"

STANDARD_INPUTS: Tuple[str, ...] = (
    "scout_signal",
    "baro_evidence",
    "enterprise_context",
    "olav_surface_context",
)

STANDARD_OUTPUTS: Tuple[AdvisorRecommendationType, ...] = (
    AdvisorRecommendationType.INSIGHT,
    AdvisorRecommendationType.BRIEFING,
    AdvisorRecommendationType.RECOMMENDATION,
    AdvisorRecommendationType.ACTION_CASE_DRAFT,
)

EVIDENCE_POLICY = (
    "Advisor output must cite source evidence refs, state limitations and keep "
    "consequential proposals as ActionCaseDraft handoff candidates."
)


def _profile(advisor_id: str, role: str, purpose: str) -> AdvisorProfile:
    return AdvisorProfile(
        advisor_id=advisor_id,
        version=PROFILE_VERSION,
        role=role,
        purpose=purpose,
        allowed_inputs=list(STANDARD_INPUTS),
        allowed_outputs=list(STANDARD_OUTPUTS),
        evidence_policy=EVIDENCE_POLICY,
        memory_policy=AdvisorMemoryPolicy.TENANT_SCOPED,
        metadata={"migration_source": "legacy_advisor_role"},
    )


ADVISOR_PROFILES: Mapping[str, AdvisorProfile] = MappingProxyType(
    {
        "ceo": _profile(
            "advisor-ceo",
            "ceo",
            "Interpret enterprise direction, strategic risk and organizational tradeoffs.",
        ),
        "cfo": _profile(
            "advisor-cfo",
            "cfo",
            "Interpret financial exposure, capital allocation and economic resilience.",
        ),
        "chro": _profile(
            "advisor-chro",
            "chro",
            "Interpret workforce, leadership, culture and organizational capacity signals.",
        ),
        "coo": _profile(
            "advisor-coo",
            "coo",
            "Interpret operational performance, delivery risk and process resilience.",
        ),
        "cto": _profile(
            "advisor-cto",
            "cto",
            "Interpret technology posture, platform delivery and engineering constraints.",
        ),
        "ciso": _profile(
            "advisor-ciso",
            "ciso",
            "Interpret security posture, threat exposure and control gaps.",
        ),
        "procurement": _profile(
            "advisor-procurement",
            "procurement",
            "Interpret supplier, sourcing, contract and third-party dependency risk.",
        ),
        "sustainability": _profile(
            "advisor-sustainability",
            "sustainability",
            "Interpret sustainability, regulatory and long-horizon impact signals.",
        ),
    }
)


def list_advisor_profiles() -> Tuple[AdvisorProfile, ...]:
    """Return all installed Advisor profiles in deterministic role order."""

    return tuple(ADVISOR_PROFILES[role] for role in sorted(ADVISOR_PROFILES))


def get_advisor_profile(role: str) -> AdvisorProfile:
    """Return one Advisor profile by role."""

    try:
        return ADVISOR_PROFILES[role]
    except KeyError as exc:
        raise KeyError(f"unknown advisor role: {role}") from exc
