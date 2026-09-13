"""Audience context resolution and strict isolation for VALO Company Voice (#674).

The AudienceContextResolver projects a CanonicalOrganizationRecord down to the
subset admissible for one audience, enforcing the issue's non-negotiable
boundaries:

  - customer records cannot enter employee/investor/supplier/regulator/public
    episodes unless explicitly authorized
  - public channels may use only PUBLIC-release-cleared records
  - investor channels cannot contain RESTRICTED (MNPI) records unless an
    authorized controlled process exists
  - no cross-audience clearance reuse
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Tuple

from .models import (
    AudienceContext,
    AudienceType,
    CanonicalOrganizationRecord,
    SensitivityLevel,
    VerifiedEvent,
    VerifiedDecision,
    VerifiedOutcome,
    GoalUpdate,
    RiskRecord,
    BlockerRecord,
    CommitmentRecord,
    MetricRecord,
)


@dataclass(frozen=True)
class ResolvedProjection:
    """Audience-specific, admissible view of the canonical record."""

    audience_id: str
    organization_id: str
    included_items: Tuple[object, ...]
    excluded_topics: Tuple[str, ...]
    max_sensitivity: SensitivityLevel


# Audience types that must never receive cross-audience personal/segment data
# unless an explicit authorization exists on the audience context.
_RESTRICTED_AUDIENCES = frozenset(
    {
        AudienceType.EMPLOYEE,
        AudienceType.INVESTOR,
        AudienceType.SUPPLIER,
        AudienceType.REGULATOR,
        AudienceType.PUBLIC,
    }
)


class AudienceContextResolver:
    """Deterministic, seeded projection with no cross-audience leakage.

    All filtering is pure and reproducible from (record, audience_context);
    the same inputs always produce the same projection, which is what makes the
    canary isolation tests deterministic.
    """

    def __init__(self, audiences: Dict[str, AudienceContext]):
        self._audiences = audiences

    def get_audience(self, audience_id: str) -> AudienceContext:
        return self._audiences[audience_id]

    def resolve(
        self,
        record: CanonicalOrganizationRecord,
        audience: AudienceContext,
    ) -> ResolvedProjection:
        """Project `record` to the admissible items for `audience`."""
        included: List[object] = []
        max_sens = SensitivityLevel.PUBLIC
        prohibited = set(audience.prohibited_topics)

        for item in record.all_items():
            # Topic allow/deny filtering (audience-scoped, explicit).
            topic = getattr(item, "topic", "")
            if topic in prohibited:
                continue
            if audience.authorized_topics and topic not in audience.authorized_topics:
                continue

            sens = item.sensitivity

            # Cross-segment isolation: confidential or restricted items (e.g.
            # customer personal data, MNPI) must NOT enter any audience unless
            # that audience explicitly authorizes the topic. This enforces the
            # issue rule that customer records cannot enter employee/investor/
            # supplier/regulator/public episodes unless explicitly authorized.
            if sens.rank() >= SensitivityLevel.CONFIDENTIAL.rank():
                if topic not in audience.authorized_topics:
                    continue

            # Isolation rule: investor channel cannot carry RESTRICTED (MNPI)
            # unless the audience explicitly authorizes it.
            if audience.audience_type == AudienceType.INVESTOR:
                if sens == SensitivityLevel.RESTRICTED and \
                        "mnpi" not in audience.advice_permissions:
                    continue

            # Isolation rule: public channel may use only PUBLIC records.
            if audience.audience_type == AudienceType.PUBLIC:
                if sens != SensitivityLevel.PUBLIC:
                    continue

            # Sensitivity ceiling.
            if sens.rank() > audience.sensitivity_ceiling.rank():
                continue

            included.append(item)
            if sens.rank() > max_sens.rank():
                max_sens = sens

        return ResolvedProjection(
            audience_id=audience.audience_id,
            organization_id=record.organization_id,
            included_items=tuple(included),
            excluded_topics=tuple(sorted(prohibited)),
            max_sensitivity=max_sens,
        )
