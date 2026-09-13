"""Claim classification for VALO Company Voice (issue #674).

Every substantive claim must be classified before clearance. This module
defines the per-class governing rules and a classifier that decides whether a
claim is admissible for a given envelope + audience, including the
regulated-advice boundary.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Tuple

from .models import AudienceContext, ClaimType, CommunicationEnvelope, SensitivityLevel


class AdviceBoundary(Enum):
    """Whether a claim class may imply regulated advice or recommendation."""

    NONE = "none"            # informational only
    GUIDANCE = "guidance"    # personalized guidance permitted within authority
    ADVICE = "advice"        # regulated advice — requires explicit authority


@dataclass(frozen=True)
class ClaimSpec:
    """Governing rules for a claim class."""

    claim_type: ClaimType
    required_evidence: bool
    required_authority: bool
    allowed_channels: Tuple[str, ...]      # empty == all channels
    required_disclosures: Tuple[str, ...]
    review_level: int                       # 0=none .. 3=high
    validity_period_days: int
    correction_behavior: str
    advice_boundary: AdviceBoundary


_CLAIM_SPECS: dict[ClaimType, ClaimSpec] = {
    ClaimType.VERIFIED_FACT: ClaimSpec(ClaimType.VERIFIED_FACT, True, False, (), ("evidence_ref",), 1, 365, "correct-and-supersede", AdviceBoundary.NONE),
    ClaimType.APPROVED_ORGANIZATIONAL_STATEMENT: ClaimSpec(ClaimType.APPROVED_ORGANIZATIONAL_STATEMENT, False, True, (), ("org-approval-ref",), 2, 180, "correct-and-supersede", AdviceBoundary.NONE),
    ClaimType.PERSONAL_ACCOUNT_FACT: ClaimSpec(ClaimType.PERSONAL_ACCOUNT_FACT, True, False, (), ("consent-ref",), 1, 365, "correct-and-supersede", AdviceBoundary.NONE),
    ClaimType.CONTRACTUAL_FACT: ClaimSpec(ClaimType.CONTRACTUAL_FACT, True, False, (), ("contract-ref",), 2, 365, "correct-and-supersede", AdviceBoundary.NONE),
    ClaimType.CALCULATED_VALUE: ClaimSpec(ClaimType.CALCULATED_VALUE, True, False, (), ("method-ref",), 1, 90, "correct-and-supersede", AdviceBoundary.NONE),
    ClaimType.GENERAL_INFORMATION: ClaimSpec(ClaimType.GENERAL_INFORMATION, False, False, (), (), 0, 365, "correct-and-supersede", AdviceBoundary.NONE),
    ClaimType.PERSONALIZED_GUIDANCE: ClaimSpec(ClaimType.PERSONALIZED_GUIDANCE, False, True, (), ("guidance-authority", "consent-ref"), 2, 30, "correct-and-supersede", AdviceBoundary.GUIDANCE),
    ClaimType.REGULATED_ADVICE: ClaimSpec(ClaimType.REGULATED_ADVICE, True, True, (), ("advice-authority", "disclosure"), 3, 30, "retract-and-notify", AdviceBoundary.ADVICE),
    ClaimType.RECOMMENDATION: ClaimSpec(ClaimType.RECOMMENDATION, True, True, (), ("recommendation-authority",), 2, 30, "correct-and-supersede", AdviceBoundary.GUIDANCE),
    ClaimType.PLANNED_ACTION: ClaimSpec(ClaimType.PLANNED_ACTION, False, True, (), ("approval-ref",), 2, 30, "correct-and-supersede", AdviceBoundary.NONE),
    ClaimType.FORECAST: ClaimSpec(ClaimType.FORECAST, False, False, (), ("uncertainty-label",), 1, 14, "correct-and-supersede", AdviceBoundary.NONE),
    ClaimType.REPORTED_CLAIM: ClaimSpec(ClaimType.REPORTED_CLAIM, True, False, (), ("source-ref",), 1, 90, "correct-and-supersede", AdviceBoundary.NONE),
    ClaimType.UNRESOLVED_QUESTION: ClaimSpec(ClaimType.UNRESOLVED_QUESTION, False, False, (), (), 0, 30, "correct-and-supersede", AdviceBoundary.NONE),
}


def get_claim_spec(claim_type: ClaimType) -> ClaimSpec:
    return _CLAIM_SPECS[claim_type]


def classify_claim(
    claim_type: ClaimType,
    envelope: CommunicationEnvelope,
    audience: AudienceContext,
    has_evidence: bool = True,
    has_authority: bool = False,
) -> bool:
    """Return True if the claim is admissible for this envelope + audience.

    Enforces:
      - required evidence present
      - required authority present (and listed in audience advice_permissions)
      - channel allowed
      - regulated-advice boundary: REGULATED_ADVICE/RECOMMENDATION only when the
        audience explicitly grants the matching advice permission
    """
    spec = get_claim_spec(claim_type)

    if spec.required_evidence and not has_evidence:
        return False
    if spec.required_authority and not has_authority:
        return False

    # Channel allow-list (empty allows any).
    if spec.allowed_channels and envelope.channel_type.value not in spec.allowed_channels:
        return False

    # Regulated-advice boundary: the audience must explicitly grant the matching
    # advice permission. Otherwise the claim must not cross the boundary.
    if spec.advice_boundary == AdviceBoundary.ADVICE:
        if "regulated_advice" not in audience.advice_permissions:
            return False
    if spec.advice_boundary == AdviceBoundary.GUIDANCE:
        if "guidance" not in audience.advice_permissions:
            return False

    # Sensitivity ceiling: a claim must not exceed the audience's ceiling unless
    # the audience explicitly authorizes that sensitivity class.
    if envelope.sensitivity_ceiling.rank() > audience.sensitivity_ceiling.rank():
        return False

    return True
