from __future__ import annotations

from collections.abc import Set as AbstractSet
from enum import Enum
from typing import Any, Final


class AssuranceCapability(str, Enum):
    """Concrete properties a source mechanism must demonstrably provide.

    Strength is NOT a linear scale: FIDO2, event-stream continuity and
    four-eyes sign-off prove *different* properties. A source satisfies a
    minimum requirement iff its capability set is a superset of the required
    capability set (`actual_capabilities >= required_capabilities`), and
    multiple mechanisms may be combined to cover the required set.
    """

    FRESHNESS_OBSERVED = "FRESHNESS_OBSERVED"
    VERSION_BOUND = "VERSION_BOUND"
    CHANGE_VISIBILITY = "CHANGE_VISIBILITY"
    IDENTITY_BOUND = "IDENTITY_BOUND"
    HARDWARE_BOUND = "HARDWARE_BOUND"
    DUAL_CONTROL = "DUAL_CONTROL"
    CRYPTOGRAPHIC_INTEGRITY = "CRYPTOGRAPHIC_INTEGRITY"
    HARDWARE_KEY_BOUND = "HARDWARE_KEY_BOUND"


# Canonical mechanism -> capability set. Unknown mechanisms resolve to no
# capabilities and therefore CANNOT self-declare strength (fail closed).
_MECHANISM_CAPABILITIES: Final[
    dict[str, frozenset[AssuranceCapability]]
] = {
    "NONE": frozenset(),
    "UNVERIFIED": frozenset(),
    "UNKNOWN": frozenset(),
    "GENERIC_ATTESTATION": frozenset(
        {AssuranceCapability.FRESHNESS_OBSERVED}
    ),
    "BASIC_TIMESTAMP": frozenset(
        {AssuranceCapability.FRESHNESS_OBSERVED}
    ),
    "UNVERSIONED_SNAPSHOT": frozenset(
        {AssuranceCapability.FRESHNESS_OBSERVED}
    ),
    "OIDC_TOKEN": frozenset(
        {
            AssuranceCapability.FRESHNESS_OBSERVED,
            AssuranceCapability.IDENTITY_BOUND,
        }
    ),
    "STATE_SNAPSHOT": frozenset(
        {
            AssuranceCapability.FRESHNESS_OBSERVED,
            AssuranceCapability.VERSION_BOUND,
        }
    ),
    "VERSION_PINNED": frozenset(
        {
            AssuranceCapability.FRESHNESS_OBSERVED,
            AssuranceCapability.VERSION_BOUND,
        }
    ),
    "AUTHORITATIVE_API": frozenset(
        {
            AssuranceCapability.FRESHNESS_OBSERVED,
            AssuranceCapability.VERSION_BOUND,
        }
    ),
    "ERP_AUTHORITATIVE_API": frozenset(
        {
            AssuranceCapability.FRESHNESS_OBSERVED,
            AssuranceCapability.VERSION_BOUND,
        }
    ),
    "ERP_COMMITTED_STATE": frozenset(
        {
            AssuranceCapability.FRESHNESS_OBSERVED,
            AssuranceCapability.VERSION_BOUND,
        }
    ),
    "EVENT_STREAM_CURSOR": frozenset(
        {
            AssuranceCapability.FRESHNESS_OBSERVED,
            AssuranceCapability.VERSION_BOUND,
            AssuranceCapability.CHANGE_VISIBILITY,
        }
    ),
    "CONTINUITY_PROVEN": frozenset(
        {
            AssuranceCapability.FRESHNESS_OBSERVED,
            AssuranceCapability.VERSION_BOUND,
            AssuranceCapability.CHANGE_VISIBILITY,
        }
    ),
    "REALTIME_ACTIVE": frozenset(
        {
            AssuranceCapability.FRESHNESS_OBSERVED,
            AssuranceCapability.VERSION_BOUND,
            AssuranceCapability.CHANGE_VISIBILITY,
        }
    ),
    "ONLINE_STATUS_CHECK": frozenset(
        {
            AssuranceCapability.FRESHNESS_OBSERVED,
            AssuranceCapability.VERSION_BOUND,
            AssuranceCapability.CHANGE_VISIBILITY,
        }
    ),
    "OIDC_HARDWARE_MFA": frozenset(
        {
            AssuranceCapability.IDENTITY_BOUND,
            AssuranceCapability.HARDWARE_BOUND,
        }
    ),
    "OIDC_FIDO2_BOUND": frozenset(
        {
            AssuranceCapability.IDENTITY_BOUND,
            AssuranceCapability.HARDWARE_BOUND,
        }
    ),
    "FOUR_EYES_ATTESTATION": frozenset({AssuranceCapability.DUAL_CONTROL}),
    "COMPLIANCE_SIGN_OFF": frozenset(
        {
            AssuranceCapability.DUAL_CONTROL,
            AssuranceCapability.CRYPTOGRAPHIC_INTEGRITY,
        }
    ),
    "CRYPTOGRAPHIC_SIGN_OFF": frozenset(
        {AssuranceCapability.CRYPTOGRAPHIC_INTEGRITY}
    ),
    "CRYPTOGRAPHIC_HSM": frozenset(
        {
            AssuranceCapability.CRYPTOGRAPHIC_INTEGRITY,
            AssuranceCapability.HARDWARE_KEY_BOUND,
        }
    ),
}


def resolve_capabilities(
    mechanism: str | None,
) -> frozenset[AssuranceCapability]:
    """Resolve a mechanism or capability name to its capability set.

    A capability name resolves to its singleton set; a known mechanism
    resolves to its declared capability set; anything else resolves to the
    empty set so callers fail closed.
    """
    if not mechanism:
        return frozenset()
    key = str(mechanism).strip().upper()
    try:
        return frozenset({AssuranceCapability(key)})
    except ValueError:
        return _MECHANISM_CAPABILITIES.get(key, frozenset())


def resolve_evidence_capabilities(evidence: Any) -> frozenset[AssuranceCapability]:
    """Union of capabilities declared by a source evidence.

    The evidence may combine mechanisms (attestation type + provenance
    assurance/strength) so several mechanisms can jointly satisfy a required
    capability set without a false linear ranking.
    """
    caps = resolve_capabilities(getattr(evidence, "attestation_type", None))
    provenance = getattr(evidence, "provenance", None)
    if isinstance(provenance, dict):
        caps |= resolve_capabilities(provenance.get("assurance_level"))
        caps |= resolve_capabilities(provenance.get("strength"))
    return caps


def is_capabilities_satisfied(
    actual: AbstractSet[AssuranceCapability],
    required: AbstractSet[AssuranceCapability],
) -> bool:
    """Capability subsumption: actual must cover every required capability."""
    return required <= actual


def is_assurance_strength_satisfied(
    actual: str | None, minimum_required: str | None
) -> bool:
    """Check whether an actual mechanism satisfies a required minimum mechanism.

    Satisfaction is decided purely by capability-set subsumption. An unknown
    or unverifiable minimum requirement fails closed.
    """
    if not minimum_required:
        return True

    required = resolve_capabilities(minimum_required)
    if not required:
        return False

    actual_caps = resolve_capabilities(actual)
    return required <= actual_caps
