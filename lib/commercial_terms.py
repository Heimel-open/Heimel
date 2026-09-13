"""Bounded commercial negotiation contracts for autonomous customer acquisition.

A negotiation mandate constrains what an agent may propose. It does not grant
execution authority and it cannot turn a customer reply into acceptance by
itself. External proposals still cross the normal governed-egress boundary;
accepted terms still require explicit customer evidence.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class NegotiationMandate:
    mandate_ref: str
    currency: str
    min_poc_price: Decimal
    max_poc_price: Decimal
    max_discount_percent: Decimal
    max_delivery_days: int
    allowed_payment_methods: tuple[str, ...]
    allowed_channels: tuple[str, ...]
    expires_at: datetime
    prohibited_terms: tuple[str, ...] = (
        "uncapped_liability",
        "ip_assignment_of_preexisting_ip",
        "unbounded_scope",
        "authority_transfer",
    )

    def __post_init__(self) -> None:
        if not self.mandate_ref.strip() or not self.currency.strip():
            raise ValueError("mandate_ref and currency are required")
        if self.min_poc_price < 0 or self.max_poc_price < self.min_poc_price:
            raise ValueError("invalid POC price bounds")
        if not Decimal("0") <= self.max_discount_percent <= Decimal("100"):
            raise ValueError("max_discount_percent must be in [0,100]")
        if self.max_delivery_days <= 0:
            raise ValueError("max_delivery_days must be positive")
        if not self.allowed_payment_methods or not self.allowed_channels:
            raise ValueError("payment methods and channels must be bounded")
        if self.expires_at.tzinfo is None:
            raise ValueError("expires_at must be timezone-aware")

    def is_active(self, now: datetime | None = None) -> bool:
        current = now or _utcnow()
        return current <= self.expires_at

    @property
    def grants_authority(self) -> bool:
        return False


@dataclass(frozen=True)
class POCProposal:
    proposal_ref: str
    mandate_ref: str
    customer_ref: str
    problem_ref: str
    spec_ref: str
    price: Decimal
    currency: str
    discount_percent: Decimal
    delivery_days: int
    payment_method: str
    channel: str
    acceptance_criteria: tuple[str, ...]
    terms: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        for name in (
            "proposal_ref",
            "mandate_ref",
            "customer_ref",
            "problem_ref",
            "spec_ref",
            "currency",
            "payment_method",
            "channel",
        ):
            if not str(getattr(self, name)).strip():
                raise ValueError(f"{name} is required")
        if not self.acceptance_criteria:
            raise ValueError("acceptance_criteria are required")


def validate_proposal(
    mandate: NegotiationMandate,
    proposal: POCProposal,
    *,
    now: datetime | None = None,
) -> tuple[bool, tuple[str, ...]]:
    """Deterministically check a proposed POC against its bounded mandate."""

    problems: list[str] = []
    if proposal.mandate_ref != mandate.mandate_ref:
        problems.append("mandate_ref_mismatch")
    if not mandate.is_active(now):
        problems.append("mandate_expired")
    if proposal.currency != mandate.currency:
        problems.append("currency_not_allowed")
    if proposal.price < mandate.min_poc_price or proposal.price > mandate.max_poc_price:
        problems.append("price_out_of_bounds")
    if proposal.discount_percent < 0 or proposal.discount_percent > mandate.max_discount_percent:
        problems.append("discount_out_of_bounds")
    if proposal.delivery_days <= 0 or proposal.delivery_days > mandate.max_delivery_days:
        problems.append("delivery_out_of_bounds")
    if proposal.payment_method not in mandate.allowed_payment_methods:
        problems.append("payment_method_not_allowed")
    if proposal.channel not in mandate.allowed_channels:
        problems.append("channel_not_allowed")
    prohibited = set(mandate.prohibited_terms).intersection(proposal.terms)
    if prohibited:
        problems.extend(f"prohibited_term:{term}" for term in sorted(prohibited))
    return (not problems, tuple(problems))


__all__ = ["NegotiationMandate", "POCProposal", "validate_proposal"]
