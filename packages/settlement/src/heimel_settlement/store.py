from __future__ import annotations

import sqlite3
from decimal import Decimal
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from . import SettlementReceipt


class SettlementReceiptStore(Protocol):
    """Idempotency surface for terminal settlement receipts."""

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
    """Durable local receipt store with atomic idempotency insertion."""

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
                    evidence_reference TEXT,
                    contract_digest TEXT
                )
                """
            )
            columns = {
                row[1]
                for row in connection.execute(
                    "PRAGMA table_info(settlement_receipts)"
                ).fetchall()
            }
            if "contract_digest" not in columns:
                connection.execute(
                    "ALTER TABLE settlement_receipts ADD COLUMN contract_digest TEXT"
                )

    @staticmethod
    def _from_row(row: tuple[object, ...]) -> SettlementReceipt:
        from . import SettlementReceipt, SettlementState

        contract_digest = row[8]
        if not isinstance(contract_digest, str) or not contract_digest:
            raise RuntimeError("stored settlement receipt lacks contract digest")
        return SettlementReceipt(
            idempotency_key=str(row[0]),
            settlement_contract_id=str(row[1]),
            consequence_id=str(row[2]),
            state=SettlementState(str(row[3])),
            amount=Decimal(str(row[4])),
            currency=str(row[5]),
            funding_reference=str(row[6]),
            evidence_reference=None if row[7] is None else str(row[7]),
            contract_digest=contract_digest,
        )

    def get(self, idempotency_key: str) -> SettlementReceipt | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT idempotency_key, settlement_contract_id, consequence_id,
                       state, amount, currency, funding_reference,
                       evidence_reference, contract_digest
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
                    state, amount, currency, funding_reference,
                    evidence_reference, contract_digest
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    receipt.contract_digest,
                ),
            )
            row = connection.execute(
                """
                SELECT idempotency_key, settlement_contract_id, consequence_id,
                       state, amount, currency, funding_reference,
                       evidence_reference, contract_digest
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
