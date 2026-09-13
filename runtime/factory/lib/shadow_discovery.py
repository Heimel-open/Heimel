"""Scoped read-only Shadow Discovery contracts for Factory OS.

Shadow Discovery is a customer-authorized discovery mode that lets a swarm of
specialized observers understand a business before a proposal is created.
It is intentionally non-authoritative: no write access, no production actions,
no hidden monitoring, and no customer commitment can be inferred from access.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class ShadowDiscoveryGrant:
    grant_ref: str
    customer_ref: str
    allowed_sources: tuple[str, ...]
    allowed_roles: tuple[str, ...]
    starts_at: datetime
    expires_at: datetime
    read_only: bool = True
    continuous: bool = False
    prohibited_data_classes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.grant_ref.strip() or not self.customer_ref.strip():
            raise ValueError("grant_ref and customer_ref are required")
        if not self.allowed_sources or not self.allowed_roles:
            raise ValueError("allowed_sources and allowed_roles must be explicit")
        if not self.read_only:
            raise ValueError("Shadow Discovery v1 is read-only only")
        if self.starts_at.tzinfo is None or self.expires_at.tzinfo is None:
            raise ValueError("grant timestamps must be timezone-aware")
        if self.expires_at <= self.starts_at:
            raise ValueError("expires_at must be after starts_at")

    def active(self, now: datetime | None = None) -> bool:
        current = now or _utcnow()
        return self.starts_at <= current <= self.expires_at

    @property
    def grants_execution_authority(self) -> bool:
        return False


@dataclass(frozen=True)
class ShadowObservation:
    observation_ref: str
    role: str
    source_ref: str
    finding: str
    evidence_refs: tuple[str, ...]
    observed_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.observation_ref.strip() or not self.role.strip():
            raise ValueError("observation_ref and role are required")
        if not self.source_ref.strip() or not self.finding.strip():
            raise ValueError("source_ref and finding are required")
        if not self.evidence_refs:
            raise ValueError("observations require evidence_refs")


@dataclass(frozen=True)
class DiscoveryOpportunity:
    opportunity_ref: str
    title: str
    problem: str
    proposed_outcome: str
    evidence_refs: tuple[str, ...]
    estimated_annual_value: Decimal | None = None
    confidence: Decimal | None = None

    def __post_init__(self) -> None:
        if not self.opportunity_ref.strip() or not self.title.strip():
            raise ValueError("opportunity_ref and title are required")
        if not self.problem.strip() or not self.proposed_outcome.strip():
            raise ValueError("problem and proposed_outcome are required")
        if not self.evidence_refs:
            raise ValueError("opportunity requires evidence_refs")
        if self.confidence is not None and not Decimal("0") <= self.confidence <= Decimal("1"):
            raise ValueError("confidence must be in [0,1]")


@dataclass(frozen=True)
class DiscoveryProposal:
    proposal_ref: str
    customer_ref: str
    opportunity_refs: tuple[str, ...]
    scope: tuple[str, ...]
    acceptance_criteria: tuple[str, ...]
    price: Decimal
    currency: str
    delivery_days: int
    required_customer_actions: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.proposal_ref.strip() or not self.customer_ref.strip():
            raise ValueError("proposal_ref and customer_ref are required")
        if not self.opportunity_refs or not self.scope or not self.acceptance_criteria:
            raise ValueError("proposal requires opportunities, scope and acceptance criteria")
        if self.price < 0 or self.delivery_days <= 0:
            raise ValueError("price must be non-negative and delivery_days positive")
        if not self.currency.strip():
            raise ValueError("currency is required")

    @property
    def grants_authority(self) -> bool:
        return False


def validate_observation_against_grant(
    grant: ShadowDiscoveryGrant,
    observation: ShadowObservation,
    *,
    now: datetime | None = None,
) -> tuple[bool, tuple[str, ...]]:
    problems: list[str] = []
    if not grant.active(now):
        problems.append("grant_not_active")
    if observation.role not in grant.allowed_roles:
        problems.append("role_not_allowed")
    if observation.source_ref not in grant.allowed_sources:
        problems.append("source_not_allowed")
    return (not problems, tuple(problems))


def default_shadow_roles() -> tuple[str, ...]:
    return (
        "process-shadow",
        "software-shadow",
        "integration-shadow",
        "data-shadow",
        "human-work-shadow",
        "risk-security-shadow",
        "product-shadow",
        "economics-shadow",
    )


__all__ = [
    "DiscoveryOpportunity",
    "DiscoveryProposal",
    "ShadowDiscoveryGrant",
    "ShadowObservation",
    "default_shadow_roles",
    "validate_observation_against_grant",
]
