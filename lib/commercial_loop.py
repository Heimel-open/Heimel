"""Straight-through commercial mission loop for VALO Factory.

This module coordinates descriptive workflow state only. It is not a new
architecture layer and exposes no authorization surface. Consequence-bearing
steps can be recorded only when the caller supplies evidence that the existing
VAIG -> REHT -> RACS -> enforcement path executed.

The loop is provider-neutral: outreach can use web/email/SMS/phone or another
approved connector; payment can use Stripe, bank transfer, smart contract or a
customer-selected provider. Provider capability never creates authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Iterable


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class CommercialState(str, Enum):
    SIGNAL_OBSERVED = "SIGNAL_OBSERVED"
    IMPACT_EVIDENCED = "IMPACT_EVIDENCED"
    PROSPECT_EVIDENCED = "PROSPECT_EVIDENCED"
    OUTREACH_READY = "OUTREACH_READY"
    OUTREACH_SENT = "OUTREACH_SENT"
    RESPONSE_OBSERVED = "RESPONSE_OBSERVED"
    POC_TERMS_PROPOSED = "POC_TERMS_PROPOSED"
    POC_TERMS_ACCEPTED = "POC_TERMS_ACCEPTED"
    POC_MISSION_CREATED = "POC_MISSION_CREATED"
    POC_VERIFIED = "POC_VERIFIED"
    POC_SUBMITTED = "POC_SUBMITTED"
    POC_APPROVED = "POC_APPROVED"
    PAYMENT_REQUESTED = "PAYMENT_REQUESTED"
    PAYMENT_CONFIRMED = "PAYMENT_CONFIRMED"
    PRODUCTION_SPEC_ACCEPTED = "PRODUCTION_SPEC_ACCEPTED"
    PRODUCTION_MISSION_CREATED = "PRODUCTION_MISSION_CREATED"
    PRODUCTION_VERIFIED = "PRODUCTION_VERIFIED"
    DEPLOYMENT_READY = "DEPLOYMENT_READY"
    CUSTOMER_ACTIVE = "CUSTOMER_ACTIVE"
    SERVICE_SIGNAL_OBSERVED = "SERVICE_SIGNAL_OBSERVED"
    SUPPORT_MISSION_CREATED = "SUPPORT_MISSION_CREATED"
    SUPPORT_VERIFIED = "SUPPORT_VERIFIED"
    OUTCOME_OBSERVED = "OUTCOME_OBSERVED"


class OpportunityOrigin(str, Enum):
    MARKET_SIGNAL = "market_signal"
    COMPETITOR_PUBLIC_SIGNAL = "competitor_public_signal"
    CUSTOMER_REQUEST = "customer_request"
    EXISTING_CUSTOMER_SIGNAL = "existing_customer_signal"


@dataclass(frozen=True)
class ExecutionGovernanceRef:
    """Evidence that an external consequence passed the canonical boundary."""

    action: str
    vaig_ref: str
    reht_ref: str
    racs_ref: str
    execution_receipt_ref: str

    def __post_init__(self) -> None:
        for name in ("action", "vaig_ref", "reht_ref", "racs_ref", "execution_receipt_ref"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")


@dataclass(frozen=True)
class IndependentVerificationRef:
    """Independent artifact verification; advisory and non-authorizing."""

    artifact_ref: str
    producer_ref: str
    judge_ref: str
    verdict: str
    evidence_refs: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.producer_ref == self.judge_ref:
            raise ValueError("producer cannot self-attest as independent judge")
        if self.verdict not in {"pass", "fail", "uncertain"}:
            raise ValueError("verdict must be pass, fail or uncertain")


@dataclass(frozen=True)
class CustomerAcceptanceRef:
    """Evidence of explicit customer acceptance of terms/spec/POC."""

    subject: str
    acceptance_ref: str
    accepted_by: str
    accepted_at: datetime = field(default_factory=_utcnow)

    def __post_init__(self) -> None:
        if not self.subject.strip() or not self.acceptance_ref.strip() or not self.accepted_by.strip():
            raise ValueError("customer acceptance requires subject, acceptance_ref and accepted_by")


@dataclass(frozen=True)
class PaymentConfirmationRef:
    """Provider receipt for settled/confirmed payment."""

    provider: str
    transaction_ref: str
    amount: str
    currency: str
    status: str = "confirmed"

    def __post_init__(self) -> None:
        if self.status not in {"confirmed", "settled"}:
            raise ValueError("payment must be confirmed or settled")
        for name in ("provider", "transaction_ref", "amount", "currency"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name} is required")


@dataclass(frozen=True)
class TransitionRecord:
    from_state: CommercialState
    to_state: CommercialState
    evidence_refs: tuple[str, ...]
    governance_ref: ExecutionGovernanceRef | None
    verification_ref: IndependentVerificationRef | None
    acceptance_ref: CustomerAcceptanceRef | None
    payment_ref: PaymentConfirmationRef | None
    recorded_at: datetime = field(default_factory=_utcnow)


_ALLOWED: dict[CommercialState, set[CommercialState]] = {
    CommercialState.SIGNAL_OBSERVED: {CommercialState.IMPACT_EVIDENCED},
    CommercialState.IMPACT_EVIDENCED: {CommercialState.PROSPECT_EVIDENCED},
    CommercialState.PROSPECT_EVIDENCED: {CommercialState.OUTREACH_READY},
    CommercialState.OUTREACH_READY: {CommercialState.OUTREACH_SENT},
    CommercialState.OUTREACH_SENT: {CommercialState.RESPONSE_OBSERVED},
    CommercialState.RESPONSE_OBSERVED: {CommercialState.POC_TERMS_PROPOSED},
    CommercialState.POC_TERMS_PROPOSED: {CommercialState.POC_TERMS_ACCEPTED},
    CommercialState.POC_TERMS_ACCEPTED: {CommercialState.POC_MISSION_CREATED},
    CommercialState.POC_MISSION_CREATED: {CommercialState.POC_VERIFIED},
    CommercialState.POC_VERIFIED: {CommercialState.POC_SUBMITTED},
    CommercialState.POC_SUBMITTED: {CommercialState.POC_APPROVED},
    CommercialState.POC_APPROVED: {
        CommercialState.PAYMENT_REQUESTED,
        CommercialState.PRODUCTION_SPEC_ACCEPTED,
    },
    CommercialState.PAYMENT_REQUESTED: {CommercialState.PAYMENT_CONFIRMED},
    CommercialState.PAYMENT_CONFIRMED: {CommercialState.PRODUCTION_SPEC_ACCEPTED},
    CommercialState.PRODUCTION_SPEC_ACCEPTED: {CommercialState.PRODUCTION_MISSION_CREATED},
    CommercialState.PRODUCTION_MISSION_CREATED: {CommercialState.PRODUCTION_VERIFIED},
    CommercialState.PRODUCTION_VERIFIED: {CommercialState.DEPLOYMENT_READY},
    CommercialState.DEPLOYMENT_READY: {CommercialState.CUSTOMER_ACTIVE},
    CommercialState.CUSTOMER_ACTIVE: {
        CommercialState.SERVICE_SIGNAL_OBSERVED,
        CommercialState.OUTCOME_OBSERVED,
    },
    CommercialState.SERVICE_SIGNAL_OBSERVED: {CommercialState.SUPPORT_MISSION_CREATED},
    CommercialState.SUPPORT_MISSION_CREATED: {CommercialState.SUPPORT_VERIFIED},
    CommercialState.SUPPORT_VERIFIED: {CommercialState.CUSTOMER_ACTIVE},
    CommercialState.OUTCOME_OBSERVED: {CommercialState.IMPACT_EVIDENCED},
}

_GOVERNED_TARGETS = {
    CommercialState.OUTREACH_SENT,
    CommercialState.POC_TERMS_PROPOSED,
    CommercialState.POC_SUBMITTED,
    CommercialState.PAYMENT_REQUESTED,
    CommercialState.CUSTOMER_ACTIVE,
}

_VERIFIED_TARGETS = {
    CommercialState.POC_VERIFIED,
    CommercialState.PRODUCTION_VERIFIED,
    CommercialState.SUPPORT_VERIFIED,
}

_ACCEPTANCE_TARGETS = {
    CommercialState.POC_TERMS_ACCEPTED,
    CommercialState.POC_APPROVED,
    CommercialState.PRODUCTION_SPEC_ACCEPTED,
}


@dataclass
class CommercialLoop:
    """One opportunity/customer loop, advanced only with explicit evidence."""

    opportunity_id: str
    origin: OpportunityOrigin = OpportunityOrigin.MARKET_SIGNAL
    state: CommercialState = CommercialState.SIGNAL_OBSERVED
    history: list[TransitionRecord] = field(default_factory=list)

    def transition(
        self,
        target: CommercialState,
        *,
        evidence_refs: Iterable[str] = (),
        governance_ref: ExecutionGovernanceRef | None = None,
        verification_ref: IndependentVerificationRef | None = None,
        acceptance_ref: CustomerAcceptanceRef | None = None,
        payment_ref: PaymentConfirmationRef | None = None,
    ) -> TransitionRecord:
        if target not in _ALLOWED.get(self.state, set()):
            raise ValueError(f"illegal commercial transition {self.state} -> {target}")

        refs = tuple(ref for ref in evidence_refs if ref)
        if not refs:
            raise ValueError("every transition requires evidence_refs")

        if target in _GOVERNED_TARGETS and governance_ref is None:
            raise ValueError(f"{target.value} requires execution governance evidence")

        if target in _VERIFIED_TARGETS:
            if verification_ref is None:
                raise ValueError(f"{target.value} requires independent verification")
            if verification_ref.verdict != "pass":
                raise ValueError(f"{target.value} requires a passing verification")

        if target in _ACCEPTANCE_TARGETS and acceptance_ref is None:
            raise ValueError(f"{target.value} requires explicit customer acceptance")

        if target is CommercialState.PAYMENT_CONFIRMED and payment_ref is None:
            raise ValueError("PAYMENT_CONFIRMED requires provider payment confirmation")

        record = TransitionRecord(
            from_state=self.state,
            to_state=target,
            evidence_refs=refs,
            governance_ref=governance_ref,
            verification_ref=verification_ref,
            acceptance_ref=acceptance_ref,
            payment_ref=payment_ref,
        )
        self.history.append(record)
        self.state = target
        return record

    @property
    def has_authority_surface(self) -> bool:
        return False


__all__ = [
    "CommercialLoop",
    "CommercialState",
    "CustomerAcceptanceRef",
    "ExecutionGovernanceRef",
    "IndependentVerificationRef",
    "OpportunityOrigin",
    "PaymentConfirmationRef",
    "TransitionRecord",
]
