from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum
from typing import Any, Protocol


class SettlementError(RuntimeError):
    pass


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
    veritas_execution_id: str
    veritas_gateway_record_id: str
    veritas_outcome_record_id: str
    expected_action_digest: str

    def __post_init__(self) -> None:
        if self.currency != "USD":
            raise SettlementError("reference contract currently requires USD")
        if self.unit_price < 0:
            raise SettlementError("unit_price must be non-negative")
        if self.unit_price.as_tuple().exponent < -6:
            raise SettlementError("unit_price supports at most 6 decimal places")
        for field_name in (
            "settlement_contract_id",
            "consequence_id",
            "payer_account",
            "funding_reference",
            "price_rule_version",
            "completion_criteria_hash",
            "evidence_requirement_hash",
            "idempotency_key",
            "veritas_execution_id",
            "veritas_gateway_record_id",
            "veritas_outcome_record_id",
            "expected_action_digest",
        ):
            if not getattr(self, field_name):
                raise SettlementError(f"{field_name} is required")


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
    """Idempotent consequence capture boundary.

    Implementations MUST treat ``idempotency_key`` as an at-most-once capture
    key. Retrying the same key after a timeout or process crash must not create
    a second economic debit.
    """

    def capture(
        self,
        *,
        payer_account: str,
        funding_reference: str,
        amount: Decimal,
        currency: str,
        idempotency_key: str,
    ) -> bool: ...


class VeritasEvidenceLedger(Protocol):
    """Minimal surface required from VeritasChainService."""

    def verify_chain(self) -> bool: ...

    def find_entry(self, record_id: str) -> Mapping[str, Any] | None: ...


@dataclass(frozen=True)
class _VerifiedConsequenceEvidence:
    gateway_record_id: str
    outcome_record_id: str
    execution_id: str
    action_digest: str
    consequence_id: str
    completion_criteria_hash: str
    evidence_requirement_hash: str
    governed_effect_completed: bool
    completion_criteria_satisfied: bool
    required_evidence_verified: bool

    @property
    def chargeable(self) -> bool:
        return (
            self.governed_effect_completed
            and self.completion_criteria_satisfied
            and self.required_evidence_verified
        )

    @property
    def evidence_reference(self) -> str:
        return f"veritas:{self.outcome_record_id}"


def _require_mapping(name: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SettlementError(f"{name} must be a mapping")
    return value


def _observed_events(entry: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    raw = entry.get("observed_events")
    if not isinstance(raw, list) or not raw:
        raise SettlementError("Veritas record has no observed events")
    events: list[Mapping[str, Any]] = []
    for item in raw:
        events.append(_require_mapping("Veritas observed event", item))
    return events


def _event_by_type(entry: Mapping[str, Any], event_type: str) -> Mapping[str, Any]:
    matches = [
        event for event in _observed_events(entry) if event.get("event_type") == event_type
    ]
    if len(matches) != 1:
        raise SettlementError(
            f"Veritas record must contain exactly one {event_type} event"
        )
    return matches[0]


def _verify_veritas_evidence(
    contract: SettlementContract,
    veritas: VeritasEvidenceLedger,
) -> _VerifiedConsequenceEvidence:
    if not veritas.verify_chain():
        raise SettlementError("Veritas WORM chain verification failed")

    gateway = veritas.find_entry(contract.veritas_gateway_record_id)
    if gateway is None:
        raise SettlementError("bound Veritas Gateway record not found")
    outcome = veritas.find_entry(contract.veritas_outcome_record_id)
    if outcome is None:
        raise SettlementError("bound Veritas outcome record not found")

    if gateway.get("execution_id") != contract.veritas_execution_id:
        raise SettlementError("Veritas Gateway execution_id mismatch")
    if outcome.get("execution_id") != contract.veritas_execution_id:
        raise SettlementError("Veritas outcome execution_id mismatch")

    gateway_event = _event_by_type(gateway, "execution_result_observed")
    if gateway_event.get("event_id") != f"execution:{contract.veritas_execution_id}":
        raise SettlementError("Veritas Gateway event id mismatch")
    gateway_provenance = _require_mapping(
        "Veritas Gateway provenance", gateway_event.get("provenance")
    )
    if gateway_provenance.get("authority_granted") is not False:
        raise SettlementError("Veritas evidence must not grant authority")
    if gateway_provenance.get("action_digest") != contract.expected_action_digest:
        raise SettlementError("Veritas action digest mismatch")
    if gateway_provenance.get("execution_status") != "succeeded":
        return _VerifiedConsequenceEvidence(
            gateway_record_id=contract.veritas_gateway_record_id,
            outcome_record_id=contract.veritas_outcome_record_id,
            execution_id=contract.veritas_execution_id,
            action_digest=contract.expected_action_digest,
            consequence_id=contract.consequence_id,
            completion_criteria_hash=contract.completion_criteria_hash,
            evidence_requirement_hash=contract.evidence_requirement_hash,
            governed_effect_completed=False,
            completion_criteria_satisfied=False,
            required_evidence_verified=False,
        )

    outcome_event = _event_by_type(outcome, "consequence_outcome_verified")
    outcome_provenance = _require_mapping(
        "Veritas outcome provenance", outcome_event.get("provenance")
    )
    if outcome_provenance.get("authority_granted") is not False:
        raise SettlementError("Veritas outcome evidence must not grant authority")

    exact_bindings = {
        "consequence_id": contract.consequence_id,
        "execution_id": contract.veritas_execution_id,
        "action_digest": contract.expected_action_digest,
        "completion_criteria_hash": contract.completion_criteria_hash,
        "evidence_requirement_hash": contract.evidence_requirement_hash,
        "gateway_record_id": contract.veritas_gateway_record_id,
    }
    for field_name, expected in exact_bindings.items():
        if outcome_provenance.get(field_name) != expected:
            raise SettlementError(f"Veritas outcome {field_name} mismatch")

    return _VerifiedConsequenceEvidence(
        gateway_record_id=contract.veritas_gateway_record_id,
        outcome_record_id=contract.veritas_outcome_record_id,
        execution_id=contract.veritas_execution_id,
        action_digest=contract.expected_action_digest,
        consequence_id=contract.consequence_id,
        completion_criteria_hash=contract.completion_criteria_hash,
        evidence_requirement_hash=contract.evidence_requirement_hash,
        governed_effect_completed=outcome_provenance.get("governed_effect_completed")
        is True,
        completion_criteria_satisfied=outcome_provenance.get(
            "completion_criteria_satisfied"
        )
        is True,
        required_evidence_verified=outcome_provenance.get(
            "required_evidence_verified"
        )
        is True,
    )


def _assert_replay_binding(
    contract: SettlementContract, receipt: SettlementReceipt
) -> None:
    expected = {
        "settlement_contract_id": contract.settlement_contract_id,
        "consequence_id": contract.consequence_id,
        "currency": contract.currency,
        "funding_reference": contract.funding_reference,
        "idempotency_key": contract.idempotency_key,
    }
    for field_name, value in expected.items():
        if getattr(receipt, field_name) != value:
            raise SettlementError(
                f"idempotency key is already bound to another {field_name}"
            )
    if receipt.state is SettlementState.SETTLED and receipt.amount != contract.unit_price:
        raise SettlementError("idempotency key is already bound to another unit_price")


# Imported after SettlementReceipt is defined so store.py can type-reference it
# without creating a package initialization cycle.
from .store import (  # noqa: E402
    InMemorySettlementReceiptStore,
    SQLiteSettlementReceiptStore,
    SettlementReceiptStore,
)


class ConsequenceSettler:
    """Settlement gate backed by Veritas evidence and an idempotency store.

    A caller cannot make a consequence chargeable by supplying booleans.
    Chargeability is derived only from exact, hash-chained Veritas records
    bound in the settlement contract before execution.

    Only terminal outcomes (SETTLED and NOT_CHARGEABLE) are persisted.
    INSUFFICIENT_FUNDS and SETTLEMENT_FAILED are retryable. Safety across a
    crash after provider capture but before receipt persistence depends on the
    PaymentRail honoring the same idempotency key on every retry.
    """

    def __init__(self, receipt_store: SettlementReceiptStore | None = None) -> None:
        self._receipt_store = receipt_store or InMemorySettlementReceiptStore()

    def settle(
        self,
        contract: SettlementContract,
        veritas: VeritasEvidenceLedger,
        payment_rail: PaymentRail,
    ) -> SettlementReceipt:
        previous = self._receipt_store.get(contract.idempotency_key)
        if previous is not None:
            _assert_replay_binding(contract, previous)
            return previous

        evidence = _verify_veritas_evidence(contract, veritas)

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
            persisted = self._receipt_store.put_if_absent(receipt)
            _assert_replay_binding(contract, persisted)
            return persisted

        try:
            captured = payment_rail.capture(
                payer_account=contract.payer_account,
                funding_reference=contract.funding_reference,
                amount=contract.unit_price,
                currency=contract.currency,
                idempotency_key=contract.idempotency_key,
            )
        except Exception:
            return SettlementReceipt(
                settlement_contract_id=contract.settlement_contract_id,
                consequence_id=contract.consequence_id,
                state=SettlementState.SETTLEMENT_FAILED,
                amount=Decimal("0"),
                currency=contract.currency,
                funding_reference=contract.funding_reference,
                evidence_reference=evidence.evidence_reference,
                idempotency_key=contract.idempotency_key,
            )

        if not captured:
            return SettlementReceipt(
                settlement_contract_id=contract.settlement_contract_id,
                consequence_id=contract.consequence_id,
                state=SettlementState.INSUFFICIENT_FUNDS,
                amount=Decimal("0"),
                currency=contract.currency,
                funding_reference=contract.funding_reference,
                evidence_reference=evidence.evidence_reference,
                idempotency_key=contract.idempotency_key,
            )

        receipt = SettlementReceipt(
            settlement_contract_id=contract.settlement_contract_id,
            consequence_id=contract.consequence_id,
            state=SettlementState.SETTLED,
            amount=contract.unit_price,
            currency=contract.currency,
            funding_reference=contract.funding_reference,
            evidence_reference=evidence.evidence_reference,
            idempotency_key=contract.idempotency_key,
        )
        persisted = self._receipt_store.put_if_absent(receipt)
        _assert_replay_binding(contract, persisted)
        return persisted


__all__ = [
    "ConsequenceSettler",
    "InMemorySettlementReceiptStore",
    "PaymentRail",
    "SQLiteSettlementReceiptStore",
    "SettlementContract",
    "SettlementError",
    "SettlementReceipt",
    "SettlementReceiptStore",
    "SettlementState",
    "VeritasEvidenceLedger",
]
