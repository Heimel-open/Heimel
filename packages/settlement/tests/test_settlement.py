from copy import deepcopy
from dataclasses import replace
from decimal import Decimal

import pytest

from heimel_settlement import (
    ConsequenceSettler,
    SQLiteSettlementReceiptStore,
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


class SequenceRail:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def capture(self, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class Veritas:
    def __init__(self, entries, valid=True):
        self.entries = deepcopy(entries)
        self.valid = valid

    def verify_chain(self):
        return self.valid

    def find_entry(self, record_id):
        return deepcopy(self.entries.get(record_id))


def contract(price: str = "0.10") -> SettlementContract:
    return SettlementContract(
        settlement_contract_id="sc-1",
        consequence_id="c-1",
        payer_account="tenant-1",
        currency="USD",
        unit_price=Decimal(price),
        funding_reference="allowance-1",
        price_rule_version="v1",
        completion_criteria_hash="sha256:" + "c" * 64,
        evidence_requirement_hash="sha256:" + "e" * 64,
        idempotency_key="settle:c-1:v1",
        veritas_execution_id="exec-1",
        veritas_gateway_record_id="gateway-execution:exec-1",
        veritas_outcome_record_id="outcome:c-1",
        expected_action_digest="a" * 64,
    )


def evidence_entries(*, status="succeeded", completed=True, criteria=True, verified=True):
    c = contract()
    return {
        c.veritas_gateway_record_id: {
            "package_id": c.veritas_gateway_record_id,
            "execution_id": c.veritas_execution_id,
            "observed_events": [
                {
                    "event_id": f"execution:{c.veritas_execution_id}",
                    "event_type": "execution_result_observed",
                    "provenance": {
                        "authority_granted": False,
                        "action_digest": c.expected_action_digest,
                        "execution_status": status,
                        "receipt_hash": "r" * 64,
                    },
                }
            ],
        },
        c.veritas_outcome_record_id: {
            "package_id": c.veritas_outcome_record_id,
            "execution_id": c.veritas_execution_id,
            "observed_events": [
                {
                    "event_id": "outcome:c-1",
                    "event_type": "consequence_outcome_verified",
                    "provenance": {
                        "authority_granted": False,
                        "consequence_id": c.consequence_id,
                        "execution_id": c.veritas_execution_id,
                        "action_digest": c.expected_action_digest,
                        "completion_criteria_hash": c.completion_criteria_hash,
                        "evidence_requirement_hash": c.evidence_requirement_hash,
                        "gateway_record_id": c.veritas_gateway_record_id,
                        "governed_effect_completed": completed,
                        "completion_criteria_satisfied": criteria,
                        "required_evidence_verified": verified,
                    },
                }
            ],
        },
    }


def test_verified_veritas_consequence_settles_prebound_price():
    rail = Rail()
    receipt = ConsequenceSettler().settle(contract(), Veritas(evidence_entries()), rail)
    assert receipt.state is SettlementState.SETTLED
    assert receipt.amount == Decimal("0.10")
    assert receipt.evidence_reference == "veritas:outcome:c-1"
    assert receipt.contract_digest == contract().contract_digest
    assert rail.calls == 1


@pytest.mark.parametrize(
    ("status", "completed", "criteria", "verified"),
    [
        ("failed", False, False, False),
        ("partial", False, False, False),
        ("blocked", False, False, False),
        ("succeeded", True, False, True),
        ("succeeded", True, True, False),
    ],
)
def test_non_verified_veritas_outcome_never_charges(status, completed, criteria, verified):
    rail = Rail()
    entries = evidence_entries(
        status=status, completed=completed, criteria=criteria, verified=verified
    )
    receipt = ConsequenceSettler().settle(contract(), Veritas(entries), rail)
    assert receipt.state is SettlementState.NOT_CHARGEABLE
    assert receipt.amount == Decimal("0")
    assert rail.calls == 0


def test_replay_returns_same_receipt_without_double_charge():
    rail = Rail()
    settler = ConsequenceSettler()
    veritas = Veritas(evidence_entries())
    first = settler.settle(contract(), veritas, rail)
    second = settler.settle(contract(), veritas, rail)
    assert first == second
    assert rail.calls == 1


def test_durable_store_survives_settler_restart_without_double_charge(tmp_path):
    path = tmp_path / "settlement.sqlite3"
    rail = Rail()
    veritas = Veritas(evidence_entries())
    first = ConsequenceSettler(SQLiteSettlementReceiptStore(path)).settle(contract(), veritas, rail)
    second = ConsequenceSettler(SQLiteSettlementReceiptStore(path)).settle(contract(), veritas, rail)
    assert first == second
    assert first.state is SettlementState.SETTLED
    assert rail.calls == 1


def test_invalid_veritas_chain_fails_closed():
    rail = Rail()
    with pytest.raises(SettlementError, match="chain verification failed"):
        ConsequenceSettler().settle(contract(), Veritas(evidence_entries(), valid=False), rail)
    assert rail.calls == 0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("consequence_id", "c-2", "consequence_id mismatch"),
        ("execution_id", "exec-2", "execution_id mismatch"),
        ("action_digest", "b" * 64, "action_digest mismatch"),
        ("completion_criteria_hash", "sha256:" + "d" * 64, "completion_criteria_hash mismatch"),
        ("evidence_requirement_hash", "sha256:" + "f" * 64, "evidence_requirement_hash mismatch"),
        ("gateway_record_id", "gateway-execution:other", "gateway_record_id mismatch"),
    ],
)
def test_outcome_must_bind_exact_contract(field, value, message):
    rail = Rail()
    entries = evidence_entries()
    entries[contract().veritas_outcome_record_id]["observed_events"][0]["provenance"][field] = value
    with pytest.raises(SettlementError, match=message):
        ConsequenceSettler().settle(contract(), Veritas(entries), rail)
    assert rail.calls == 0


def test_gateway_action_digest_must_match_contract():
    rail = Rail()
    entries = evidence_entries()
    entries[contract().veritas_gateway_record_id]["observed_events"][0]["provenance"]["action_digest"] = "b" * 64
    with pytest.raises(SettlementError, match="action digest mismatch"):
        ConsequenceSettler().settle(contract(), Veritas(entries), rail)
    assert rail.calls == 0


def test_missing_bound_veritas_record_fails_closed():
    rail = Rail()
    entries = evidence_entries()
    del entries[contract().veritas_outcome_record_id]
    with pytest.raises(SettlementError, match="outcome record not found"):
        ConsequenceSettler().settle(contract(), Veritas(entries), rail)
    assert rail.calls == 0


def test_insufficient_funds_is_retryable_after_topup():
    rail = SequenceRail([False, True])
    settler = ConsequenceSettler()
    veritas = Veritas(evidence_entries())
    first = settler.settle(contract(), veritas, rail)
    second = settler.settle(contract(), veritas, rail)
    assert first.state is SettlementState.INSUFFICIENT_FUNDS
    assert second.state is SettlementState.SETTLED
    assert rail.calls == 2


def test_transient_payment_failure_is_retryable_with_same_idempotency_key():
    rail = SequenceRail([RuntimeError("timeout"), True])
    settler = ConsequenceSettler()
    veritas = Veritas(evidence_entries())
    first = settler.settle(contract(), veritas, rail)
    second = settler.settle(contract(), veritas, rail)
    assert first.state is SettlementState.SETTLEMENT_FAILED
    assert second.state is SettlementState.SETTLED
    assert rail.calls == 2


def test_replay_key_cannot_be_rebound_to_different_contract():
    rail = Rail()
    settler = ConsequenceSettler()
    veritas = Veritas(evidence_entries())
    settler.settle(contract(), veritas, rail)
    rebound = replace(contract(), settlement_contract_id="sc-other")
    with pytest.raises(SettlementError, match="another settlement contract"):
        settler.settle(rebound, veritas, rail)
    assert rail.calls == 1


def test_not_chargeable_replay_key_cannot_be_rebound_to_different_price():
    rail = Rail()
    settler = ConsequenceSettler()
    entries = evidence_entries(criteria=False)
    veritas = Veritas(entries)
    first = settler.settle(contract(), veritas, rail)
    assert first.state is SettlementState.NOT_CHARGEABLE
    with pytest.raises(SettlementError, match="another settlement contract"):
        settler.settle(contract("0.20"), veritas, rail)
    assert rail.calls == 0


def test_unit_price_precision_matches_schema_limit():
    with pytest.raises(SettlementError, match="at most 6 decimal places"):
        contract("0.0000001")
