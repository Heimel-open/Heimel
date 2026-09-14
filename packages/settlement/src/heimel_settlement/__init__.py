from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Protocol


class SettlementError(RuntimeError):
    pass


class OutcomeState(str, Enum):
    VERIFIED = "VERIFIED"
    DENY = "DENY"
    ESCALATE = "ESCALATE"
    FAILED_EFFECT = "FAILED_EFFECT"
    UNVERIFIED_OUTCOME = "UNVERIFIED_OUTCOME"


class SettlementState(str, Enum):
    SETTLED = "SETTLED"
    NOT_CHARGEABLE = "NOT_CHARGEABLE"
    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    SETTLEMENT_FAILED = "SETTLEMENT_FAILED"


@dataclass(frozen=True)
class SettlementContract:
    settlement_contract_id: str
    consequence_id: str
    payer_account: str
    currency: str
    unit_price: Decimal
    funding_reference: str
    price_rule_version: str
    completion_criteria_hash: str
    evidence_requirement_hash: str
    idempotency_key: str

    def __post_init__(self) -> None:
        if self.currency != "USD":
            raise SettlementError("reference contract currently requires USD")
        if self.unit_price < 0:
            raise SettlementError("unit_price must be non-negative")
        for field_name in (
            "settlement_contract_id",
            "consequence_id",
            "payer_account",
            "funding_reference",
            "price_rule_version",
            "completion_criteria_hash",
            "evidence_requirement_hash",
            "idempotency_key",
        ):
            if not getattr(self, field_name):
                raise SettlementError(f"{field_name} is required")


@dataclass(frozen=True)
class ConsequenceEvidence:
    consequence_id: str
    outcome_state: OutcomeState
    governed_effect_completed: bool
    completion_criteria_satisfied: bool
    required_evidence_verified: bool
    evidence_reference: str | None = None

    @property
    def chargeable(self) -> bool:
        return (
            self.outcome_state is OutcomeState.VERIFIED
            and self.governed_effect_completed
            and self.completion_criteria_satisfied
            and self.required_evidence_verified
            and bool(self.evidence_reference)
        )


@dataclass(frozen=True)
class SettlementReceipt:
    settlement_contract_id: str
    consequence_id: str
    state: SettlementState
    amount: Decimal
    currency: str
    funding_reference: str
    evidence_reference: str | None
    idempotency_key: str


class PaymentRail(Protocol):
    def capture(
        self,
        *,
        payer_account: str,
        funding_reference: str,
        amount: Decimal,
        currency: str,
        idempotency_key: str,
    ) -> bool: ...


class ConsequenceSettler:
    """Deterministic reference settlement gate.

    It does not meter or bill governed ticks. It only settles a pre-bound price
    after one consequence has completed and its required evidence is verified.
    """

    def __init__(self) -> None:
        self._receipts: dict[str, SettlementReceipt] = {}

    def settle(
        self,
        contract: SettlementContract,
        evidence: ConsequenceEvidence,
        payment_rail: PaymentRail,
    ) -> SettlementReceipt:
        previous = self._receipts.get(contract.idempotency_key)
        if previous is not None:
            return previous

        if evidence.consequence_id != contract.consequence_id:
            raise SettlementError("evidence is not bound to the contracted consequence")

        if not evidence.chargeable:
            receipt = SettlementReceipt(
                settlement_contract_id=contract.settlement_contract_id,
                consequence_id=contract.consequence_id,
                state=SettlementState.NOT_CHARGEABLE,
                amount=Decimal("0"),
                currency=contract.currency,
                funding_reference=contract.funding_reference,
                evidence_reference=evidence.evidence_reference,
                idempotency_key=contract.idempotency_key,
            )
            self._receipts[contract.idempotency_key] = receipt
            return receipt

        try:
            captured = payment_rail.capture(
                payer_account=contract.payer_account,
                funding_reference=contract.funding_reference,
                amount=contract.unit_price,
                currency=contract.currency,
                idempotency_key=contract.idempotency_key,
            )
        except Exception as exc:  # provider boundary: fail closed
            raise SettlementError("payment rail failed closed") from exc

        state = SettlementState.SETTLED if captured else SettlementState.INSUFFICIENT_FUNDS
        receipt = SettlementReceipt(
            settlement_contract_id=contract.settlement_contract_id,
            consequence_id=contract.consequence_id,
            state=state,
            amount=contract.unit_price if captured else Decimal("0"),
            currency=contract.currency,
            funding_reference=contract.funding_reference,
            evidence_reference=evidence.evidence_reference,
            idempotency_key=contract.idempotency_key,
        )
        self._receipts[contract.idempotency_key] = receipt
        return receipt


__all__ = [
    "ConsequenceEvidence",
    "ConsequenceSettler",
    "OutcomeState",
    "PaymentRail",
    "SettlementContract",
    "SettlementError",
    "SettlementReceipt",
    "SettlementState",
]
