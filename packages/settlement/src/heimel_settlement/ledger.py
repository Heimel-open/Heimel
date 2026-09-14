from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path


class AccountingLedgerError(RuntimeError):
    pass


@dataclass(frozen=True)
class Posting:
    account: str
    amount: Decimal


class SQLiteDoubleEntryLedger:
    """Immutable local double-entry ledger for funding and consequence settlement.

    Positive postings are debits and negative postings are credits. Every
    transaction MUST sum to zero. ``transaction_id`` is idempotent and bound to
    the canonical transaction digest, so replay is safe and rebinding fails.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS journal_transactions (
                    transaction_id TEXT PRIMARY KEY,
                    transaction_digest TEXT NOT NULL,
                    reference TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS journal_postings (
                    transaction_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    account TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    PRIMARY KEY (transaction_id, position),
                    FOREIGN KEY (transaction_id) REFERENCES journal_transactions(transaction_id)
                );
                """
            )

    @staticmethod
    def _digest(transaction_id: str, reference: str, postings: tuple[Posting, ...]) -> str:
        payload = {
            "transaction_id": transaction_id,
            "reference": reference,
            "postings": [
                {"account": posting.account, "amount": str(posting.amount)}
                for posting in postings
            ],
        }
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        return "sha256:" + hashlib.sha256(raw).hexdigest()

    def post(
        self,
        *,
        transaction_id: str,
        reference: str,
        postings: tuple[Posting, ...],
    ) -> str:
        if not transaction_id or not reference:
            raise AccountingLedgerError("transaction_id and reference are required")
        if len(postings) < 2:
            raise AccountingLedgerError("double-entry transaction requires at least two postings")
        if any(not p.account or not p.amount.is_finite() for p in postings):
            raise AccountingLedgerError("invalid posting")
        if sum((p.amount for p in postings), Decimal("0")) != Decimal("0"):
            raise AccountingLedgerError("journal transaction is not balanced")

        digest = self._digest(transaction_id, reference, postings)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT transaction_digest FROM journal_transactions WHERE transaction_id = ?",
                (transaction_id,),
            ).fetchone()
            if existing is not None:
                if existing[0] != digest:
                    raise AccountingLedgerError(
                        "transaction_id is already bound to another journal transaction"
                    )
                return digest
            connection.execute(
                "INSERT INTO journal_transactions(transaction_id, transaction_digest, reference) VALUES (?, ?, ?)",
                (transaction_id, digest, reference),
            )
            connection.executemany(
                "INSERT INTO journal_postings(transaction_id, position, account, amount) VALUES (?, ?, ?, ?)",
                [
                    (transaction_id, index, posting.account, str(posting.amount))
                    for index, posting in enumerate(postings)
                ],
            )
        return digest

    def record_funding(
        self,
        *,
        funding_id: str,
        customer_account: str,
        amount: Decimal,
        provider_asset_account: str = "asset:payment-provider",
    ) -> str:
        if amount <= 0:
            raise AccountingLedgerError("funding amount must be positive")
        return self.post(
            transaction_id=f"funding:{funding_id}",
            reference=funding_id,
            postings=(
                Posting(provider_asset_account, amount),
                Posting(f"liability:customer:{customer_account}", -amount),
            ),
        )

    def record_consequence_settlement(
        self,
        *,
        consequence_id: str,
        customer_account: str,
        amount: Decimal,
        revenue_account: str = "revenue:governed-consequence",
    ) -> str:
        if amount <= 0:
            raise AccountingLedgerError("settlement amount must be positive")
        available = self.available_balance(customer_account)
        if available < amount:
            raise AccountingLedgerError("insufficient customer balance")
        return self.post(
            transaction_id=f"consequence:{consequence_id}",
            reference=consequence_id,
            postings=(
                Posting(f"liability:customer:{customer_account}", amount),
                Posting(revenue_account, -amount),
            ),
        )

    def account_balance(self, account: str) -> Decimal:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT amount FROM journal_postings WHERE account = ?", (account,)
            ).fetchall()
        return sum((Decimal(row[0]) for row in rows), Decimal("0"))

    def available_balance(self, customer_account: str) -> Decimal:
        return -self.account_balance(f"liability:customer:{customer_account}")


__all__ = ["AccountingLedgerError", "Posting", "SQLiteDoubleEntryLedger"]
