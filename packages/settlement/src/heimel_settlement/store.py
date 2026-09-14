from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from . import SettlementReceipt


class SettlementReceiptStore(Protocol):
    """Idempotency surface for terminal settlement receipts.

    Production implementations MUST make ``put_if_absent`` atomic across
    processes. Only terminal receipts belong in this store; retryable states
    such as insufficient funds or transient rail failure must not be persisted.
    """

    def get(self, idempotency_key: str) -> SettlementReceipt | None: ...

    def put_if_absent(self, receipt: SettlementReceipt) -> SettlementReceipt: ...


class InMemorySettlementReceiptStore:
    """Process-local, thread-safe reference receipt store."""

    def __init__(self) -> None:
        self._receipts: dict[str, SettlementReceipt] = {}
        self._lock = Lock()

    def get(self, idempotency_key: str) -> SettlementReceipt | None:
        with self._lock:
            return self._receipts.get(idempotency_key)

    def put_if_absent(self, receipt: SettlementReceipt) -> SettlementReceipt:
        with self._lock:
            existing = self._receipts.get(receipt.idempotency_key)
            if existing is not None:
                return existing
            self._receipts[receipt.idempotency_key] = receipt
            return receipt


class SQLiteSettlementReceiptStore:
    """Durable local receipt store with atomic idempotency insertion.

    SQLite's PRIMARY KEY on ``idempotency_key`` provides process-safe
    compare-and-set semantics for a local deployment. Distributed deployments
    can implement the same protocol on their transactional datastore.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30.0)
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS settlement_receipts (
                    idempotency_key TEXT PRIMARY KEY,
                    settlement_contract_id TEXT NOT NULL,
                    consequence_id TEXT NOT NULL,
                    state TEXT NOT NULL,
                    amount TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    funding_reference TEXT NOT NULL,
                    evidence_reference TEXT
                )
                """
            )

    @staticmethod
    def _from_row(row: tuple[str, ...]) -> SettlementReceipt:
        # Local import avoids a package initialization cycle.
        from . import SettlementReceipt, SettlementState

        return SettlementReceipt(
            idempotency_key=row[0],
            settlement_contract_id=row[1],
            consequence_id=row[2],
            state=SettlementState(row[3]),
            amount=Decimal(row[4]),
            currency=row[5],
            funding_reference=row[6],
            evidence_reference=row[7],
        )

    def get(self, idempotency_key: str) -> SettlementReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT idempotency_key, settlement_contract_id, consequence_id,
                       state, amount, currency, funding_reference, evidence_reference
                FROM settlement_receipts
                WHERE idempotency_key = ?
                """,
                (idempotency_key,),
            ).fetchone()
        return None if row is None else self._from_row(row)

    def put_if_absent(self, receipt: SettlementReceipt) -> SettlementReceipt:
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT OR IGNORE INTO settlement_receipts (
                    idempotency_key, settlement_contract_id, consequence_id,
                    state, amount, currency, funding_reference, evidence_reference
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    receipt.idempotency_key,
                    receipt.settlement_contract_id,
                    receipt.consequence_id,
                    receipt.state.value,
                    str(receipt.amount),
                    receipt.currency,
                    receipt.funding_reference,
                    receipt.evidence_reference,
                ),
            )
            row = connection.execute(
                """
                SELECT idempotency_key, settlement_contract_id, consequence_id,
                       state, amount, currency, funding_reference, evidence_reference
                FROM settlement_receipts
                WHERE idempotency_key = ?
                """,
                (receipt.idempotency_key,),
            ).fetchone()
        if row is None:
            raise RuntimeError("failed to persist settlement receipt")
        return self._from_row(row)


__all__ = [
    "InMemorySettlementReceiptStore",
    "SQLiteSettlementReceiptStore",
    "SettlementReceiptStore",
]
