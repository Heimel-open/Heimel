from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping

from lib.opportunity_factory import RevenueLane


class DoneTrack(str, Enum):
    KNOW = "know"
    DECIDE = "decide"
    CREATE = "create"
    CONVINCE = "convince"
    OBTAIN = "obtain"
    OPERATE = "operate"
    ASSURE = "assure"
    COORDINATE = "coordinate"


class PaymentModel(str, Enum):
    DONE_ESCROW = "done_escrow"
    MILESTONE_ESCROW = "milestone_escrow"


@dataclass(frozen=True)
class PaymentContract:
    """Payment is secured before execution and released only for accepted Done.

    `provider` is deliberately provider-neutral. Stripe/payment processors are not
    treated as escrow unless their actual product and legal role support it.
    """

    amount: float
    currency: str = "USD"
    model: PaymentModel = PaymentModel.DONE_ESCROW
    provider: str | None = None
    funded_before_execution: bool = True
    release_condition: str = "accepted done state"
    dispute_process_required: bool = True
    refund_if_not_done: bool = True

    def __post_init__(self) -> None:
        if self.amount < 0:
            raise ValueError("payment amount must be >= 0")
        if not self.currency.strip():
            raise ValueError("currency is required")
        if not self.funded_before_execution:
            raise ValueError("Need-Done requires payment security before execution")
        if not self.release_condition.strip():
            raise ValueError("release condition is required")
        if not self.dispute_process_required:
            raise ValueError("escrow requires an explicit dispute process")


@dataclass(frozen=True)
class NeedDoneContract:
    """Classifies paid service work by the customer's desired done-state.

    A lane is only an observed market form. The contract captures the need,
    expected outcome, acceptance condition, required capabilities and the
    irreducible human or licensed remainder. Commercial execution can attach a
    PaymentContract so cash is secured before work and released only after the
    agreed Done acceptance gate passes.
    """

    need: str
    done: str
    track: DoneTrack
    deliverables: tuple[str, ...] = ()
    acceptance_gate: str = "buyer acceptance"
    required_capabilities: tuple[str, ...] = ()
    automatable_fraction: float = 0.0
    human_remainder: tuple[str, ...] = ()
    licensed_role_required: bool = False
    representation_required: bool = False
    payment: PaymentContract | None = None

    def __post_init__(self) -> None:
        if not self.need.strip() or not self.done.strip():
            raise ValueError("need and done are required")
        if not 0 <= self.automatable_fraction <= 1:
            raise ValueError("automatable_fraction must be between 0 and 1")
        if (self.licensed_role_required or self.representation_required) and not self.human_remainder:
            raise ValueError("regulated or representative work requires an explicit human remainder")


LANE_TRACK: Mapping[RevenueLane, DoneTrack] = {
    RevenueLane.AI_EVALS: DoneTrack.ASSURE,
    RevenueLane.UGC_ADS: DoneTrack.CREATE,
    RevenueLane.CLIPPING: DoneTrack.CREATE,
    RevenueLane.AFFILIATE: DoneTrack.CONVINCE,
    RevenueLane.LEAD_GEN: DoneTrack.OBTAIN,
    RevenueLane.LOCALIZATION: DoneTrack.CREATE,
    RevenueLane.ECOMMERCE_CATALOG: DoneTrack.CREATE,
    RevenueLane.PAID_RESEARCH: DoneTrack.KNOW,
    RevenueLane.ARTICLE_WRITING: DoneTrack.CREATE,
    RevenueLane.PR_COMMS: DoneTrack.CONVINCE,
    RevenueLane.PUBLIC_AFFAIRS: DoneTrack.CONVINCE,
    RevenueLane.RFP_PROPOSALS: DoneTrack.OBTAIN,
    RevenueLane.GRANT_WRITING: DoneTrack.OBTAIN,
    RevenueLane.MARKET_INTELLIGENCE: DoneTrack.KNOW,
    RevenueLane.DUE_DILIGENCE: DoneTrack.DECIDE,
    RevenueLane.LEGAL_RESEARCH: DoneTrack.KNOW,
    RevenueLane.CONTRACT_REVIEW: DoneTrack.ASSURE,
    RevenueLane.COMPLIANCE_GRC: DoneTrack.ASSURE,
    RevenueLane.BOOKKEEPING: DoneTrack.OPERATE,
    RevenueLane.TAX_RESEARCH_PREP: DoneTrack.ASSURE,
    RevenueLane.RECRUITING_SOURCING: DoneTrack.OBTAIN,
    RevenueLane.PROCUREMENT_SOURCING: DoneTrack.OBTAIN,
}


TRACK_QUESTIONS: Mapping[DoneTrack, str] = {
    DoneTrack.KNOW: "What does the buyer need to know, with what evidence?",
    DoneTrack.DECIDE: "What decision must become defensible and ready to make?",
    DoneTrack.CREATE: "What artifact must exist and pass which quality gate?",
    DoneTrack.CONVINCE: "Whose understanding or behavior must change, within what mandate?",
    DoneTrack.OBTAIN: "What resource, customer, candidate, contract or funding must be acquired?",
    DoneTrack.OPERATE: "What recurring process must reliably reach its required state?",
    DoneTrack.ASSURE: "What must be checked, reconciled, compliant or proven?",
    DoneTrack.COORDINATE: "What people, tasks, dependencies or resources must be synchronized?",
}


def track_for_lane(lane: RevenueLane) -> DoneTrack:
    return LANE_TRACK[lane]
