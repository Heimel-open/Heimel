from __future__ import annotations

from threading import Lock
from typing import Protocol

from . import SettlementReceipt


class SettlementReceiptStore(Protocol):
    """Durable idempotency surface for settlement receipts.

    Production implementations MUST make ``put_if_absent`` atomic across
    processes. The in-memory implementation is only a local/reference store.
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
