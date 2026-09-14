from decimal import Decimal

import pytest

from heimel_settlement import (
    ConsequenceEvidence,
    ConsequenceSettler,
    OutcomeState,
    SettlementContract,
    SettlementError,
    SettlementState,
)


class Rail:
    def __init__(self, result: bool = True):
        self.result = result
        self.calls = 0

    def capture(self, **kwargs):
        self.calls += 1
        return self.result


def contract(price: str = "0.10") -> SettlementContract:
    return SettlementContract(
        settlement_contract_id="sc-1",
        consequence_id="c-1",
        payer_account="tenant-1",
        currency="USD",
        unit_price=Decimal(price),
        funding_reference="allowance-1",
        price_rule_version="v1",
        completion_criteria_hash="completion-hash",
        evidence_requirement_hash="evidence-hash",
        idempotency_key="settle:c-1:v1",
    )


def verified() -> ConsequenceEvidence:
    return ConsequenceEvidence(
        consequence_id="c-1",
        outcome_state=OutcomeState.VERIFIED,
        governed_effect_completed=True,
        completion_criteria_satisfied=True,
        required_evidence_verified=True,
        evidence_reference="veritas:receipt-1",
    )


def test_verified_consequence_settles_prebound_price():
    rail = Rail()
    receipt = ConsequenceSettler().settle(contract(), verified(), rail)
    assert receipt.state is SettlementState.SETTLED
    assert receipt.amount == Decimal("0.10")
    assert rail.calls == 1


@pytest.mark.parametrize(
    "state",
    [
        OutcomeState.DENY,
        OutcomeState.ESCALATE,
        OutcomeState.FAILED_EFFECT,
        OutcomeState.UNVERIFIED_OUTCOME,
    ],
)
def test_non_completed_or_unverified_consequence_never_charges(state):
    rail = Rail()
    evidence = ConsequenceEvidence(
        consequence_id="c-1",
        outcome_state=state,
        governed_effect_completed=state is OutcomeState.UNVERIFIED_OUTCOME,
        completion_criteria_satisfied=False,
        required_evidence_verified=False,
    )
    receipt = ConsequenceSettler().settle(contract(), evidence, rail)
    assert receipt.state is SettlementState.NOT_CHARGEABLE
    assert receipt.amount == Decimal("0")
    assert rail.calls == 0


def test_replay_returns_same_receipt_without_double_charge():
    rail = Rail()
    settler = ConsequenceSettler()
    first = settler.settle(contract(), verified(), rail)
    second = settler.settle(contract(), verified(), rail)
    assert first == second
    assert rail.calls == 1


def test_evidence_must_bind_to_exact_consequence():
    evidence = verified()
    wrong = ConsequenceEvidence(
        consequence_id="c-2",
        outcome_state=evidence.outcome_state,
        governed_effect_completed=True,
        completion_criteria_satisfied=True,
        required_evidence_verified=True,
        evidence_reference=evidence.evidence_reference,
    )
    with pytest.raises(SettlementError, match="contracted consequence"):
        ConsequenceSettler().settle(contract(), wrong, Rail())


def test_insufficient_funds_fails_closed_without_charge():
    rail = Rail(result=False)
    receipt = ConsequenceSettler().settle(contract(), verified(), rail)
    assert receipt.state is SettlementState.INSUFFICIENT_FUNDS
    assert receipt.amount == Decimal("0")
    assert rail.calls == 1
