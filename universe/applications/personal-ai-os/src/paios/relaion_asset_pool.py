"""relAIon asset-pool demonstrator.

Turns an under-used personally owned asset into a governed capability proposal.
PAIOS discovers and proposes; it never books, grants access, charges, insures, or
executes. Any consequential effect must cross VAIG + REHT and execute outside
PAIOS through the governed VALO effect path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Sequence

from paios.proposal import ActionEnvelope


@dataclass(frozen=True)
class ReservedWindow:
    start: str
    end: str
    reason: str = "owner_use"


@dataclass(frozen=True)
class AssetProfile:
    asset_id: str
    owner_id: str
    kind: str
    location: str
    annual_cost: float
    estimated_value: float
    used_days_last_year: int
    owner_reserved: Sequence[ReservedWindow] = field(default_factory=tuple)
    emotional_value: float = 0.0

    @property
    def unused_days_last_year(self) -> int:
        return max(0, 365 - self.used_days_last_year)

    @property
    def cost_per_used_day(self) -> float:
        if self.used_days_last_year <= 0:
            return self.annual_cost
        return self.annual_cost / self.used_days_last_year


@dataclass(frozen=True)
class ServiceRequirement:
    capability: str
    sla: str
    max_price: float


@dataclass(frozen=True)
class RiskQuote:
    risk: str
    exposure: float
    probability: float
    premium: float
    underwriter: str

    @classmethod
    def price(
        cls,
        *,
        risk: str,
        exposure: float,
        probability: float,
        loading: float,
        underwriter: str,
    ) -> "RiskQuote":
        if exposure < 0:
            raise ValueError("exposure must be non-negative")
        if not 0 <= probability <= 1:
            raise ValueError("probability must be between 0 and 1")
        if loading < 1:
            raise ValueError("loading must be >= 1")
        return cls(
            risk=risk,
            exposure=exposure,
            probability=probability,
            premium=exposure * probability * loading,
            underwriter=underwriter,
        )


@dataclass(frozen=True)
class PoolOffer:
    asset: AssetProfile
    available_days: int
    owner_days_reserved: int
    expected_gross_yield: float
    expected_service_cost: float
    expected_risk_premium: float
    expected_net_yield: float
    services: Sequence[ServiceRequirement]
    risks: Sequence[RiskQuote]


def build_pool_offer(
    asset: AssetProfile,
    *,
    owner_days_reserved: int,
    expected_daily_revenue: float,
    expected_occupancy: float,
    services: Iterable[ServiceRequirement],
    risks: Iterable[RiskQuote],
) -> PoolOffer:
    """Price a non-binding asset-pool opportunity.

    This is discovery/evaluation only. It creates no listing or access right.
    """
    if owner_days_reserved < 0 or owner_days_reserved > 365:
        raise ValueError("owner_days_reserved must be between 0 and 365")
    if expected_daily_revenue < 0:
        raise ValueError("expected_daily_revenue must be non-negative")
    if not 0 <= expected_occupancy <= 1:
        raise ValueError("expected_occupancy must be between 0 and 1")

    available_days = max(0, 365 - owner_days_reserved)
    booked_days = available_days * expected_occupancy
    gross = booked_days * expected_daily_revenue

    service_items = tuple(services)
    risk_items = tuple(risks)
    service_cost = booked_days * sum(s.max_price for s in service_items)
    risk_premium = sum(r.premium for r in risk_items)
    net = gross - service_cost - risk_premium

    return PoolOffer(
        asset=asset,
        available_days=available_days,
        owner_days_reserved=owner_days_reserved,
        expected_gross_yield=gross,
        expected_service_cost=service_cost,
        expected_risk_premium=risk_premium,
        expected_net_yield=net,
        services=service_items,
        risks=risk_items,
    )


def propose_pool_allocation(
    offer: PoolOffer,
    *,
    actor_id: str,
    mandate_id: str,
    policy_id: str,
) -> ActionEnvelope:
    """Build the RACS-compatible proposal for REHT/VAIG evaluation.

    No marketplace publication, access grant, service order, insurance bind, or
    payment is performed here.
    """
    return ActionEnvelope(
        action_type="ASSET_POOL_ALLOCATE",
        actor={"id": actor_id, "role": "personal_agent"},
        target={
            "asset_id": offer.asset.asset_id,
            "asset_kind": offer.asset.kind,
            "owner_id": offer.asset.owner_id,
        },
        requested_effect={
            "effect": "make_unused_capacity_available",
            "available_days": offer.available_days,
            "owner_days_reserved": offer.owner_days_reserved,
            "preserve_owner_title": True,
            "requires_fresh_match_before_access": True,
        },
        authority_context={
            "mandate_id": mandate_id,
            "principal": offer.asset.owner_id,
            "scope": ["pool_offer"],
            "excludes": ["transfer_title", "grant_access", "bind_insurance", "charge"],
        },
        policy_context={"policy_id": policy_id, "fail_closed": True},
        evidence_package={
            "used_days_last_year": offer.asset.used_days_last_year,
            "unused_days_last_year": offer.asset.unused_days_last_year,
            "annual_cost": offer.asset.annual_cost,
            "cost_per_used_day": offer.asset.cost_per_used_day,
            "emotional_value": offer.asset.emotional_value,
            "expected_gross_yield": offer.expected_gross_yield,
            "expected_service_cost": offer.expected_service_cost,
            "expected_risk_premium": offer.expected_risk_premium,
            "expected_net_yield": offer.expected_net_yield,
        },
        environment_state={
            "location": offer.asset.location,
            "reserved_windows": [w.__dict__ for w in offer.asset.owner_reserved],
            "service_requirements": [s.__dict__ for s in offer.services],
        },
        risk_context={
            "principle": "every_transaction_has_risk_every_risk_has_a_price",
            "quotes": [r.__dict__ for r in offer.risks],
            "must_be_bound_at_consequence_time": True,
        },
    )
