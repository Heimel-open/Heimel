from decimal import Decimal

import pytest

from heimel_settlement.ledger import (
    AccountingLedgerError,
    Posting,
    SQLiteDoubleEntryLedger,
)


def test_funding_and_consequence_settlement_are_balanced(tmp_path):
    ledger = SQLiteDoubleEntryLedger(tmp_path / "ledger.sqlite")
    ledger.record_funding(
        funding_id="fund-1", customer_account="tenant-1", amount=Decimal("10.00")
    )
    assert ledger.available_balance("tenant-1") == Decimal("10.00")

    ledger.record_consequence_settlement(
        consequence_id="c-1", customer_account="tenant-1", amount=Decimal("0.10")
    )
    assert ledger.available_balance("tenant-1") == Decimal("9.90")
    assert ledger.account_balance("revenue:governed-consequence") == Decimal("-0.10")


def test_replay_is_idempotent(tmp_path):
    ledger = SQLiteDoubleEntryLedger(tmp_path / "ledger.sqlite")
    first = ledger.record_funding(
        funding_id="fund-1", customer_account="tenant-1", amount=Decimal("10.00")
    )
    second = ledger.record_funding(
        funding_id="fund-1", customer_account="tenant-1", amount=Decimal("10.00")
    )
    assert first == second
    assert ledger.available_balance("tenant-1") == Decimal("10.00")


def test_transaction_id_cannot_be_rebound(tmp_path):
    ledger = SQLiteDoubleEntryLedger(tmp_path / "ledger.sqlite")
    ledger.record_funding(
        funding_id="fund-1", customer_account="tenant-1", amount=Decimal("10.00")
    )
    with pytest.raises(AccountingLedgerError, match="already bound"):
        ledger.record_funding(
            funding_id="fund-1", customer_account="tenant-1", amount=Decimal("11.00")
        )


def test_unbalanced_transaction_is_rejected(tmp_path):
    ledger = SQLiteDoubleEntryLedger(tmp_path / "ledger.sqlite")
    with pytest.raises(AccountingLedgerError, match="not balanced"):
        ledger.post(
            transaction_id="bad-1",
            reference="bad",
            postings=(Posting("a", Decimal("1")), Posting("b", Decimal("-0.9"))),
        )


def test_cannot_settle_more_than_available_balance(tmp_path):
    ledger = SQLiteDoubleEntryLedger(tmp_path / "ledger.sqlite")
    ledger.record_funding(
        funding_id="fund-1", customer_account="tenant-1", amount=Decimal("1.00")
    )
    with pytest.raises(AccountingLedgerError, match="insufficient"):
        ledger.record_consequence_settlement(
            consequence_id="c-1", customer_account="tenant-1", amount=Decimal("1.01")
        )
