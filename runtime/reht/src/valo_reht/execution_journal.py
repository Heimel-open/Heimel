"""Durable non-authoritative execution intent/recovery journal.

The journal closes the observability gap around process death at the consequence
boundary. It never grants authority and never retries an external effect. Its
only job is to make crash state explicit and to permit evidence-only recovery
when a terminal receipt was durably prepared before the crash.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from threading import Lock
from typing import Protocol

from .consistency import ConsistencyScope
from .evidence_closure import EvidenceClosure, ExecutionEvidenceClosureSink
from .runtime_interlocks import ExecutionReceipt, canonical_digest


class ExecutionJournalError(RuntimeError):
    """Durable execution-journal state could not be read or transitioned."""


class JournalState(str, Enum):
    INTENT_OPEN = "INTENT_OPEN"
    EFFECT_INVOKING = "EFFECT_INVOKING"
    RECEIPT_READY = "RECEIPT_READY"
    EVIDENCE_CLOSING = "EVIDENCE_CLOSING"
    CLOSED = "CLOSED"


class RecoveryClassification(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    INDETERMINATE_EFFECT = "INDETERMINATE_EFFECT"
    READY_FOR_EVIDENCE_CLOSURE = "READY_FOR_EVIDENCE_CLOSURE"
    INDETERMINATE_EVIDENCE_CLOSURE = "INDETERMINATE_EVIDENCE_CLOSURE"
    CLOSED = "CLOSED"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class ExecutionJournalEntry:
    permit_ref: str
    state: JournalState
    action_digest: str
    execution_context_hash: str
    clearance_ref: str
    effect_name: str
    receipt: ExecutionReceipt | None = None
    veritas_ref: str | None = None
    kernel_ref: str | None = None
    authority_granted: bool = False

    def __post_init__(self) -> None:
        if self.authority_granted:
            raise ValueError("execution journal cannot grant authority")


@dataclass(frozen=True)
class ExecutionRecovery:
    permit_ref: str
    state: JournalState | None
    classification: RecoveryClassification
    receipt: ExecutionReceipt | None = None
    veritas_ref: str | None = None
    kernel_ref: str | None = None
    authority_granted: bool = False

    def __post_init__(self) -> None:
        if self.authority_granted:
            raise ValueError("execution recovery cannot grant authority")


class ExecutionRecoveryRequired(RuntimeError):
    """An earlier attempt exists and must be reconciled without effect replay."""

    def __init__(self, recovery: ExecutionRecovery) -> None:
        super().__init__(
            f"EXECUTION_RECOVERY_REQUIRED:{recovery.classification.value}:"
            f"{recovery.permit_ref}"
        )
        self.recovery = recovery


class PermitStateReader(Protocol):
    def is_consumed(self, permit_ref: str) -> bool: ...


class ExecutionJournal(Protocol):
    production_safe: bool
    consistency_scope: ConsistencyScope

    def open_intent(
        self,
        *,
        permit_ref: str,
        action_digest: str,
        execution_context_hash: str,
        clearance_ref: str,
        effect_name: str,
    ) -> bool: ...

    def mark_effect_invoking(self, permit_ref: str) -> None: ...

    def mark_receipt_ready(self, permit_ref: str, receipt: ExecutionReceipt) -> None: ...

    def mark_evidence_closing(self, permit_ref: str) -> None: ...

    def mark_closed(self, permit_ref: str, closure: EvidenceClosure) -> None: ...

    def get(self, permit_ref: str) -> ExecutionJournalEntry | None: ...


def _assert_receipt_binding(
    *,
    permit_ref: str,
    action_digest: str,
    execution_context_hash: str,
    clearance_ref: str,
    effect_name: str,
    receipt: ExecutionReceipt,
) -> None:
    if receipt.authority_granted:
        raise ExecutionJournalError("execution receipt cannot grant authority")
    if receipt.reason == "PERMIT_REPLAY":
        raise ExecutionJournalError(
            "consumed permit without prior journal state is indeterminate"
        )
    expected = {
        "permit_ref": permit_ref,
        "action_digest": action_digest,
        "execution_context_hash": execution_context_hash,
        "clearance_ref": clearance_ref,
        "effect_name": effect_name,
        "reht_decision": "ALLOW",
    }
    observed = {
        "permit_ref": receipt.permit_ref,
        "action_digest": receipt.action_digest,
        "execution_context_hash": receipt.execution_context_hash,
        "clearance_ref": receipt.clearance_ref,
        "effect_name": receipt.effect_name,
        "reht_decision": receipt.reht_decision,
    }
    if observed != expected:
        raise ExecutionJournalError("execution receipt does not match durable intent bindings")
    core = receipt.to_dict()
    receipt_id = core.pop("receipt_id")
    if receipt_id != "sha256:" + canonical_digest(core):
        raise ExecutionJournalError("execution receipt digest mismatch")


def _assert_closure_binding(receipt: ExecutionReceipt, closure: EvidenceClosure) -> None:
    if closure.authority_granted:
        raise ExecutionJournalError("execution evidence cannot grant authority")
    if closure.receipt_id != receipt.receipt_id:
        raise ExecutionJournalError("execution evidence receipt mismatch")
    if not closure.closed or not closure.veritas_ref or not closure.kernel_ref:
        raise ExecutionJournalError("closed journal transition requires closed evidence references")


class DevelopmentExecutionJournal:
    """Process-local journal for explicit development/test mode only."""

    production_safe = False
    consistency_scope = ConsistencyScope.PROCESS_LOCAL

    def __init__(self) -> None:
        self._lock = Lock()
        self._entries: dict[str, ExecutionJournalEntry] = {}

    def open_intent(
        self,
        *,
        permit_ref: str,
        action_digest: str,
        execution_context_hash: str,
        clearance_ref: str,
        effect_name: str,
    ) -> bool:
        with self._lock:
            if permit_ref in self._entries:
                return False
            self._entries[permit_ref] = ExecutionJournalEntry(
                permit_ref=permit_ref,
                state=JournalState.INTENT_OPEN,
                action_digest=action_digest,
                execution_context_hash=execution_context_hash,
                clearance_ref=clearance_ref,
                effect_name=effect_name,
            )
            return True

    def _transition(
        self,
        permit_ref: str,
        *,
        expected: tuple[JournalState, ...],
        target: JournalState,
        receipt: ExecutionReceipt | None = None,
        closure: EvidenceClosure | None = None,
    ) -> None:
        with self._lock:
            current = self._entries.get(permit_ref)
            if current is None:
                raise ExecutionJournalError("execution journal entry missing")
            if current.state not in expected:
                raise ExecutionJournalError(
                    f"invalid execution journal transition: {current.state.value}->{target.value}"
                )
            if receipt is not None:
                _assert_receipt_binding(
                    permit_ref=current.permit_ref,
                    action_digest=current.action_digest,
                    execution_context_hash=current.execution_context_hash,
                    clearance_ref=current.clearance_ref,
                    effect_name=current.effect_name,
                    receipt=receipt,
                )
            if closure is not None:
                if current.receipt is None:
                    raise ExecutionJournalError("closed journal entry requires terminal receipt")
                if self.production_safe:
                    _assert_closure_binding(current.receipt, closure)
                else:
                    if closure.authority_granted:
                        raise ExecutionJournalError(
                            "execution evidence cannot grant authority"
                        )
                    if closure.receipt_id != current.receipt.receipt_id:
                        raise ExecutionJournalError(
                            "execution evidence receipt mismatch"
                        )
            self._entries[permit_ref] = replace(
                current,
                state=target,
                receipt=receipt if receipt is not None else current.receipt,
                veritas_ref=closure.veritas_ref if closure is not None else current.veritas_ref,
                kernel_ref=closure.kernel_ref if closure is not None else current.kernel_ref,
                authority_granted=False,
            )

    def mark_effect_invoking(self, permit_ref: str) -> None:
        self._transition(
            permit_ref,
            expected=(JournalState.INTENT_OPEN,),
            target=JournalState.EFFECT_INVOKING,
        )

    def mark_receipt_ready(self, permit_ref: str, receipt: ExecutionReceipt) -> None:
        self._transition(
            permit_ref,
            expected=(JournalState.INTENT_OPEN, JournalState.EFFECT_INVOKING),
            target=JournalState.RECEIPT_READY,
            receipt=receipt,
        )

    def mark_evidence_closing(self, permit_ref: str) -> None:
        self._transition(
            permit_ref,
            expected=(JournalState.RECEIPT_READY,),
            target=JournalState.EVIDENCE_CLOSING,
        )

    def mark_closed(self, permit_ref: str, closure: EvidenceClosure) -> None:
        self._transition(
            permit_ref,
            expected=(JournalState.EVIDENCE_CLOSING,),
            target=JournalState.CLOSED,
            closure=closure,
        )

    def get(self, permit_ref: str) -> ExecutionJournalEntry | None:
        with self._lock:
            return self._entries.get(permit_ref)

    def list_unresolved(self) -> tuple[ExecutionJournalEntry, ...]:
        with self._lock:
            return tuple(
                entry
                for entry in self._entries.values()
                if entry.state is not JournalState.CLOSED
            )


class SQLiteExecutionJournal:
    """Same-host durable execution journal backed by SQLite WAL/FULL sync.

    This is a reference implementation for processes that share one correctly
    locking SQLite database. It is not a distributed consensus guarantee.
    """

    production_safe = True
    consistency_scope = ConsistencyScope.SAME_HOST_SHARED

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        configured = path or os.environ.get("VALO_REHT_EXECUTION_JOURNAL_DB")
        if configured is None or not str(configured).strip():
            raise ValueError(
                "execution journal requires path or VALO_REHT_EXECUTION_JOURNAL_DB"
            )
        self.path = Path(configured)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10.0, isolation_level=None)
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS execution_journal (
                        permit_ref TEXT PRIMARY KEY,
                        state TEXT NOT NULL,
                        action_digest TEXT NOT NULL,
                        execution_context_hash TEXT NOT NULL,
                        clearance_ref TEXT NOT NULL,
                        effect_name TEXT NOT NULL,
                        receipt_json TEXT,
                        veritas_ref TEXT,
                        kernel_ref TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                    """
                )
        except sqlite3.Error as exc:
            raise ExecutionJournalError(
                f"execution journal initialization failed: {exc}"
            ) from exc

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat().replace("+00:00", "Z")

    def open_intent(
        self,
        *,
        permit_ref: str,
        action_digest: str,
        execution_context_hash: str,
        clearance_ref: str,
        effect_name: str,
    ) -> bool:
        if not all(
            isinstance(value, str) and value
            for value in (
                permit_ref,
                action_digest,
                execution_context_hash,
                clearance_ref,
                effect_name,
            )
        ):
            raise ExecutionJournalError("execution intent bindings are required")
        stamp = self._now()
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    connection.execute(
                        """
                        INSERT INTO execution_journal (
                            permit_ref, state, action_digest,
                            execution_context_hash, clearance_ref, effect_name,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            permit_ref,
                            JournalState.INTENT_OPEN.value,
                            action_digest,
                            execution_context_hash,
                            clearance_ref,
                            effect_name,
                            stamp,
                            stamp,
                        ),
                    )
                except sqlite3.IntegrityError:
                    connection.rollback()
                    return False
                connection.commit()
                return True
        except sqlite3.Error as exc:
            raise ExecutionJournalError(
                f"execution intent write failed: {exc}"
            ) from exc

    def _transition(
        self,
        permit_ref: str,
        *,
        expected: tuple[JournalState, ...],
        target: JournalState,
        receipt: ExecutionReceipt | None = None,
        closure: EvidenceClosure | None = None,
    ) -> None:
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                row = connection.execute(
                    """
                    SELECT state, action_digest, execution_context_hash,
                           clearance_ref, effect_name, receipt_json
                    FROM execution_journal WHERE permit_ref = ?
                    """,
                    (permit_ref,),
                ).fetchone()
                if row is None:
                    connection.rollback()
                    raise ExecutionJournalError("execution journal entry missing")
                current_state = JournalState(row[0])
                if current_state not in expected:
                    connection.rollback()
                    raise ExecutionJournalError(
                        f"invalid execution journal transition: {current_state.value}->{target.value}"
                    )
                current_receipt = (
                    ExecutionReceipt(**json.loads(row[5])) if row[5] is not None else None
                )
                if receipt is not None:
                    _assert_receipt_binding(
                        permit_ref=permit_ref,
                        action_digest=row[1],
                        execution_context_hash=row[2],
                        clearance_ref=row[3],
                        effect_name=row[4],
                        receipt=receipt,
                    )
                if closure is not None:
                    if current_receipt is None:
                        connection.rollback()
                        raise ExecutionJournalError("closed journal entry requires terminal receipt")
                    _assert_receipt_binding(
                        permit_ref=permit_ref,
                        action_digest=row[1],
                        execution_context_hash=row[2],
                        clearance_ref=row[3],
                        effect_name=row[4],
                        receipt=current_receipt,
                    )
                    _assert_closure_binding(current_receipt, closure)
                receipt_json = (
                    json.dumps(receipt.to_dict(), sort_keys=True, separators=(",", ":"))
                    if receipt is not None
                    else None
                )
                updates = ["state = ?", "updated_at = ?"]
                values: list[str | None] = [target.value, self._now()]
                if receipt_json is not None:
                    updates.append("receipt_json = ?")
                    values.append(receipt_json)
                if closure is not None:
                    updates.extend(["veritas_ref = ?", "kernel_ref = ?"])
                    values.extend([closure.veritas_ref, closure.kernel_ref])
                values.append(permit_ref)
                connection.execute(
                    f"UPDATE execution_journal SET {', '.join(updates)} WHERE permit_ref = ?",
                    tuple(values),
                )
                connection.commit()
        except ExecutionJournalError:
            raise
        except (json.JSONDecodeError, sqlite3.Error, TypeError, ValueError) as exc:
            raise ExecutionJournalError(
                f"execution journal transition failed: {exc}"
            ) from exc

    def mark_effect_invoking(self, permit_ref: str) -> None:
        self._transition(
            permit_ref,
            expected=(JournalState.INTENT_OPEN,),
            target=JournalState.EFFECT_INVOKING,
        )

    def mark_receipt_ready(self, permit_ref: str, receipt: ExecutionReceipt) -> None:
        self._transition(
            permit_ref,
            expected=(JournalState.INTENT_OPEN, JournalState.EFFECT_INVOKING),
            target=JournalState.RECEIPT_READY,
            receipt=receipt,
        )

    def mark_evidence_closing(self, permit_ref: str) -> None:
        self._transition(
            permit_ref,
            expected=(JournalState.RECEIPT_READY,),
            target=JournalState.EVIDENCE_CLOSING,
        )

    def mark_closed(self, permit_ref: str, closure: EvidenceClosure) -> None:
        self._transition(
            permit_ref,
            expected=(JournalState.EVIDENCE_CLOSING,),
            target=JournalState.CLOSED,
            closure=closure,
        )

    def get(self, permit_ref: str) -> ExecutionJournalEntry | None:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    """
                    SELECT state, action_digest, execution_context_hash,
                           clearance_ref, effect_name, receipt_json,
                           veritas_ref, kernel_ref
                    FROM execution_journal
                    WHERE permit_ref = ?
                    """,
                    (permit_ref,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise ExecutionJournalError(
                f"execution journal read failed: {exc}"
            ) from exc
        if row is None:
            return None
        try:
            receipt = (
                ExecutionReceipt(**json.loads(row[5])) if row[5] is not None else None
            )
            if receipt is not None:
                _assert_receipt_binding(
                    permit_ref=permit_ref,
                    action_digest=row[1],
                    execution_context_hash=row[2],
                    clearance_ref=row[3],
                    effect_name=row[4],
                    receipt=receipt,
                )
            entry = ExecutionJournalEntry(
                permit_ref=permit_ref,
                state=JournalState(row[0]),
                action_digest=row[1],
                execution_context_hash=row[2],
                clearance_ref=row[3],
                effect_name=row[4],
                receipt=receipt,
                veritas_ref=row[6],
                kernel_ref=row[7],
            )
            if entry.state is JournalState.CLOSED:
                if entry.receipt is None or not entry.veritas_ref or not entry.kernel_ref:
                    raise ExecutionJournalError("closed journal entry is incomplete")
            return entry
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            raise ExecutionJournalError(f"execution journal entry invalid: {exc}") from exc

    def list_unresolved(self) -> tuple[ExecutionJournalEntry, ...]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    "SELECT permit_ref FROM execution_journal WHERE state != ? ORDER BY created_at",
                    (JournalState.CLOSED.value,),
                ).fetchall()
        except sqlite3.Error as exc:
            raise ExecutionJournalError(
                f"execution journal scan failed: {exc}"
            ) from exc
        return tuple(
            entry
            for permit_ref, in rows
            if (entry := self.get(permit_ref)) is not None
        )


def inspect_recovery(
    *,
    journal: ExecutionJournal,
    permit_store: PermitStateReader,
    permit_ref: str,
) -> ExecutionRecovery:
    entry = journal.get(permit_ref)
    if entry is None:
        return ExecutionRecovery(
            permit_ref=permit_ref,
            state=None,
            classification=RecoveryClassification.UNKNOWN,
        )
    if entry.state is JournalState.CLOSED:
        return ExecutionRecovery(
            permit_ref=permit_ref,
            state=entry.state,
            classification=RecoveryClassification.CLOSED,
            receipt=entry.receipt,
            veritas_ref=entry.veritas_ref,
            kernel_ref=entry.kernel_ref,
        )
    if entry.state is JournalState.RECEIPT_READY:
        return ExecutionRecovery(
            permit_ref=permit_ref,
            state=entry.state,
            classification=RecoveryClassification.READY_FOR_EVIDENCE_CLOSURE,
            receipt=entry.receipt,
        )
    if entry.state is JournalState.EVIDENCE_CLOSING:
        return ExecutionRecovery(
            permit_ref=permit_ref,
            state=entry.state,
            classification=RecoveryClassification.INDETERMINATE_EVIDENCE_CLOSURE,
            receipt=entry.receipt,
        )
    if entry.state is JournalState.EFFECT_INVOKING:
        return ExecutionRecovery(
            permit_ref=permit_ref,
            state=entry.state,
            classification=RecoveryClassification.INDETERMINATE_EFFECT,
        )
    if entry.state is JournalState.INTENT_OPEN:
        try:
            consumed = permit_store.is_consumed(permit_ref)
        except Exception:
            return ExecutionRecovery(
                permit_ref=permit_ref,
                state=entry.state,
                classification=RecoveryClassification.UNKNOWN,
            )
        return ExecutionRecovery(
            permit_ref=permit_ref,
            state=entry.state,
            classification=(
                RecoveryClassification.INDETERMINATE_EFFECT
                if consumed
                else RecoveryClassification.NOT_STARTED
            ),
        )
    return ExecutionRecovery(
        permit_ref=permit_ref,
        state=entry.state,
        classification=RecoveryClassification.UNKNOWN,
    )


def reconcile_receipt_ready(
    *,
    journal: ExecutionJournal,
    evidence_sink: ExecutionEvidenceClosureSink,
    permit_ref: str,
) -> EvidenceClosure:
    entry = journal.get(permit_ref)
    if entry is None or entry.state is not JournalState.RECEIPT_READY or entry.receipt is None:
        raise ExecutionJournalError(
            "only RECEIPT_READY execution can be reconciled without effect replay"
        )
    journal.mark_evidence_closing(permit_ref)
    closure = evidence_sink.close(entry.receipt)
    _assert_closure_binding(entry.receipt, closure)
    journal.mark_closed(permit_ref, closure)
    return closure


__all__ = [
    "DevelopmentExecutionJournal",
    "ExecutionJournal",
    "ExecutionJournalEntry",
    "ExecutionJournalError",
    "ExecutionRecovery",
    "ExecutionRecoveryRequired",
    "JournalState",
    "PermitStateReader",
    "RecoveryClassification",
    "SQLiteExecutionJournal",
    "inspect_recovery",
    "reconcile_receipt_ready",
]
