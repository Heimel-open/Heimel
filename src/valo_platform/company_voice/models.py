"""Core data objects for VALO Company Voice (issue #674).

This module defines the frozen, immutable dataclasses that form the canonical
governed reality and the audience-specific projections. No generation, I/O or
network access belongs here — this is the shared contract every later phase
reuses.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Tuple

# Reuse the existing VALO time-window primitive rather than redefining one.
from src.valo_platform.time_window_enforcer import TimeWindow


class SensitivityLevel(Enum):
    """Information sensitivity ladder. Order matters: rank() increases with sensitivity."""

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"  # includes material non-public information (MNPI)

    def rank(self) -> int:
        return _SENSITIVITY_ORDER[self]


_SENSITIVITY_ORDER = {
    SensitivityLevel.PUBLIC: 0,
    SensitivityLevel.INTERNAL: 1,
    SensitivityLevel.CONFIDENTIAL: 2,
    SensitivityLevel.RESTRICTED: 3,
}


class AudienceType(Enum):
    """Legitimate recipient classes for Company Voice artifacts."""

    EMPLOYEE = "employee"
    CUSTOMER = "customer"
    SUPPLIER = "supplier"
    PARTNER = "partner"
    INVESTOR = "investor"
    REGULATOR = "regulator"
    PUBLIC = "public"


class ChannelType(Enum):
    """Delivery channels. Each artifact is bound to exactly one envelope/channel."""

    PRIVATE_PODCAST = "private_podcast"
    APP = "app"
    EMAIL = "email"
    MOBILE = "mobile"
    INTRANET = "intranet"
    CUSTOMER_PORTAL = "customer_portal"
    SUPPLIER_PORTAL = "supplier_portal"
    INVESTOR_PORTAL = "investor_portal"
    REGULATOR_PORTAL = "regulator_portal"
    PUBLIC_PODCAST = "public_podcast"


class PublicationMode(Enum):
    """How a cleared artifact may be published."""

    DRAFT_ONLY = "draft_only"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    SHADOW_MODE = "shadow_mode"
    PRE_APPROVED_AUTOMATIC = "pre_approved_automatic"
    EVENT_TRIGGERED_REVIEW = "event_triggered_review"
    PUBLIC_RELEASE_REVIEW = "public_release_review"


class ClaimType(Enum):
    """Claim taxonomy — every substantive claim must be classified before clearance."""

    VERIFIED_FACT = "verified_fact"
    APPROVED_ORGANIZATIONAL_STATEMENT = "approved_organizational_statement"
    PERSONAL_ACCOUNT_FACT = "personal_account_fact"
    CONTRACTUAL_FACT = "contractual_fact"
    CALCULATED_VALUE = "calculated_value"
    GENERAL_INFORMATION = "general_information"
    PERSONALIZED_GUIDANCE = "personalized_guidance"
    REGULATED_ADVICE = "regulated_advice"
    RECOMMENDATION = "recommendation"
    PLANNED_ACTION = "planned_action"
    FORECAST = "forecast"
    REPORTED_CLAIM = "reported_claim"
    UNRESOLVED_QUESTION = "unresolved_question"


# ---------------------------------------------------------------------------
# Canonical record item types. Lightweight frozen records that carry the
# evidence reference + sensitivity + topic used by the audience resolver.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VerifiedEvent:
    event_id: str
    topic: str
    summary: str
    evidence_refs: Tuple[str, ...]
    sensitivity: SensitivityLevel


@dataclass(frozen=True)
class VerifiedDecision:
    decision_id: str
    topic: str
    summary: str
    evidence_refs: Tuple[str, ...]
    sensitivity: SensitivityLevel


@dataclass(frozen=True)
class VerifiedOutcome:
    outcome_id: str
    topic: str
    summary: str
    evidence_refs: Tuple[str, ...]
    sensitivity: SensitivityLevel


@dataclass(frozen=True)
class GoalUpdate:
    goal_id: str
    topic: str
    summary: str
    evidence_refs: Tuple[str, ...]
    sensitivity: SensitivityLevel


@dataclass(frozen=True)
class RiskRecord:
    risk_id: str
    topic: str
    summary: str
    evidence_refs: Tuple[str, ...]
    sensitivity: SensitivityLevel


@dataclass(frozen=True)
class BlockerRecord:
    blocker_id: str
    topic: str
    summary: str
    evidence_refs: Tuple[str, ...]
    sensitivity: SensitivityLevel


@dataclass(frozen=True)
class CommitmentRecord:
    commitment_id: str
    topic: str
    summary: str
    evidence_refs: Tuple[str, ...]
    sensitivity: SensitivityLevel


@dataclass(frozen=True)
class MetricRecord:
    metric_id: str
    topic: str
    summary: str
    evidence_refs: Tuple[str, ...]
    sensitivity: SensitivityLevel


@dataclass(frozen=True)
class CanonicalOrganizationRecord:
    """The single canonical organizational reality.

    Every audience-specific episode derives from one of these. No generated
    artifact may inherit clearance from another audience variant (issue #674).
    """

    record_id: str
    organization_id: str
    period_start: datetime
    period_end: datetime
    events: Tuple[VerifiedEvent, ...] = field(default_factory=tuple)
    decisions: Tuple[VerifiedDecision, ...] = field(default_factory=tuple)
    outcomes: Tuple[VerifiedOutcome, ...] = field(default_factory=tuple)
    goal_updates: Tuple[GoalUpdate, ...] = field(default_factory=tuple)
    risks: Tuple[RiskRecord, ...] = field(default_factory=tuple)
    blockers: Tuple[BlockerRecord, ...] = field(default_factory=tuple)
    commitments: Tuple[CommitmentRecord, ...] = field(default_factory=tuple)
    published_metrics: Tuple[MetricRecord, ...] = field(default_factory=tuple)
    evidence_refs: Tuple[str, ...] = field(default_factory=tuple)
    sensitivity: SensitivityLevel = SensitivityLevel.PUBLIC
    source_scope_hash: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def all_items(self):
        """Yield every record item so resolvers can filter uniformly."""
        for grp in (
            self.events,
            self.decisions,
            self.outcomes,
            self.goal_updates,
            self.risks,
            self.blockers,
            self.commitments,
            self.published_metrics,
        ):
            yield from grp


@dataclass(frozen=True)
class AudienceContext:
    """Projection rules for one recipient class. Determines what may appear."""

    audience_id: str
    audience_type: AudienceType
    relationship: str
    jurisdiction: str
    authorized_topics: Tuple[str, ...]
    prohibited_topics: Tuple[str, ...]
    sensitivity_ceiling: SensitivityLevel
    disclosure_profile: str
    advice_permissions: Tuple[str, ...]
    valid_from: datetime
    valid_until: Optional[datetime] = None


@dataclass(frozen=True)
class PersonalContextProjection:
    """Purpose-bound, revocable personal context for one subscriber."""

    subject_id: str
    context_version: str
    relevant_products: Tuple[str, ...]
    active_cases: Tuple[str, ...]
    goals: Tuple[str, ...]
    commitments: Tuple[str, ...]
    known_information: Tuple[str, ...]
    preferred_language: str
    preferred_duration_seconds: int
    accessibility_profile: Optional[str]
    excluded_topics: Tuple[str, ...]
    consent_refs: Tuple[str, ...]


@dataclass(frozen=True)
class CommunicationEnvelope:
    """Every artifact must carry exactly one envelope before generation/clearance."""

    envelope_id: str
    publisher_id: str
    purpose_id: str
    audience_context_ref: str
    personal_context_ref: Optional[str]
    source_record_ref: str
    channel_type: ChannelType
    authorized_topics: Tuple[str, ...]
    prohibited_topics: Tuple[str, ...]
    sensitivity_ceiling: SensitivityLevel
    claim_policy_ref: str
    disclosure_policy_ref: str
    approval_requirements: Tuple[str, ...]
    validity_window: TimeWindow
    retention_policy_ref: str
    correction_policy_ref: str


def compute_source_scope_hash(evidence_refs: Tuple[str, ...]) -> str:
    """Deterministic hash of the source scope — proves which evidence a record used."""
    joined = "\n".join(sorted(evidence_refs))
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()
