from __future__ import annotations

import hashlib
import json
import os
from multiprocessing import get_all_start_methods, get_context
from pathlib import Path
from typing import Any

import pytest

from valo_reht import (
    BoundaryEffect,
    EffectBoundary,
    ExecutionJournalError,
    ExecutionRecoveryRequired,
    JournalState,
    RecoveryClassification,
    SQLiteExecutionJournal,
    SQLitePermitStore,
    inspect_recovery,
    reconcile_receipt_ready,
)
from valo_reht.contracts import DecisionResult
from valo_reht.evidence_closure import EvidenceClosure
from valo_reht.runtime_interlocks import build_execution_receipt


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _process_context():
    method = "fork" if "fork" in get_all_start_methods() else "spawn"
    return get_context(method)


def _durable_marker(path: str, value: str) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(value + "\n")
        handle.flush()
        os.fsync(handle.fileno())


class _StaticReht:
    def __init__(self, permit_ref: str) -> None:
        self.permit_ref = permit_ref

    def authorize(
        self,
        execution_context: dict[str, Any],
        action_contract: dict[str, Any],
    ) -> DecisionResult:
        return DecisionResult(
            decision="ALLOW",
            clearance_ref="clearance:crash",
            permit_ref=self.permit_ref,
            execution_context_hash=_digest(execution_context),
        )


class _ClosedSink:
    def __init__(self, events: list[str] | None = None) -> None:
        self.events = events if events is not None else []

    def close(self, receipt) -> EvidenceClosure:
        self.events.append(receipt.receipt_id)
        return EvidenceClosure(
            receipt_id=receipt.receipt_id,
            veritas_ref=f"veritas-worm:{receipt.receipt_id}",
            kernel_ref=f"kernel:{receipt.receipt_id}",
            closed=True,
        )


def _action() -> dict[str, Any]:
    return {"action_id": "action:crash", "action_type": "WRITE", "target": "target:1"}


def _context(_: dict[str, Any]) -> dict[str, Any]:
    return {"state_version": 1, "actor_id": "actor:1"}


def _receipt(permit_ref: str):
    return build_execution_receipt(
        status="COMMITTED",
        action=_action(),
        execution_context_hash=_digest(_context(_action())),
        reht_decision="ALLOW",
        clearance_ref="clearance:crash",
        permit_ref=permit_ref,
        effect_name="crash-effect",
        effect_result={"ok": True},
    )


def _hard_exit_from_effect(
    permit_db: str,
    journal_db: str,
    marker: str,
    permit_ref: str,
) -> None:
    boundary = EffectBoundary(
        SQLitePermitStore(permit_db),
        evidence_sink=_ClosedSink(),
        execution_journal=SQLiteExecutionJournal(journal_db),
    )

    def effect(_: dict[str, Any]) -> None:
        _durable_marker(marker, "EFFECT")
        os._exit(73)

    boundary.commit(
        reht=_StaticReht(permit_ref),
        context_factory=_context,
        action_contract=_action(),
        effect=BoundaryEffect.seal("crash-effect", effect),
    )
    os._exit(99)


def _hard_exit_after_receipt_ready(
    permit_db: str,
    journal_db: str,
    marker: str,
    permit_ref: str,
) -> None:
    store = SQLitePermitStore(permit_db)
    journal = SQLiteExecutionJournal(journal_db)
    context_hash = _digest(_context(_action()))
    assert journal.open_intent(
        permit_ref=permit_ref,
        action_digest=_digest(_action()),
        execution_context_hash=context_hash,
        clearance_ref="clearance:crash",
        effect_name="crash-effect",
    )
    assert store.consume_once(permit_ref)
    journal.mark_effect_invoking(permit_ref)
    _durable_marker(marker, "EFFECT")
    journal.mark_receipt_ready(permit_ref, _receipt(permit_ref))
    os._exit(74)


def _hard_exit_during_evidence_closing(
    permit_db: str,
    journal_db: str,
    permit_ref: str,
) -> None:
    store = SQLitePermitStore(permit_db)
    journal = SQLiteExecutionJournal(journal_db)
    context_hash = _digest(_context(_action()))
    assert journal.open_intent(
        permit_ref=permit_ref,
        action_digest=_digest(_action()),
        execution_context_hash=context_hash,
        clearance_ref="clearance:crash",
        effect_name="crash-effect",
    )
    assert store.consume_once(permit_ref)
    journal.mark_effect_invoking(permit_ref)
    journal.mark_receipt_ready(permit_ref, _receipt(permit_ref))
    journal.mark_evidence_closing(permit_ref)
    os._exit(75)


def test_journal_requires_explicit_path_or_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VALO_REHT_EXECUTION_JOURNAL_DB", raising=False)
    with pytest.raises(ValueError, match="execution journal requires path"):
        SQLiteExecutionJournal()


def test_intent_open_classifies_not_started_until_permit_is_consumed(tmp_path: Path) -> None:
    store = SQLitePermitStore(tmp_path / "permits.sqlite3")
    journal = SQLiteExecutionJournal(tmp_path / "journal.sqlite3")
    permit = "permit:not-started"
    assert journal.open_intent(
        permit_ref=permit,
        action_digest=_digest(_action()),
        execution_context_hash=_digest(_context(_action())),
        clearance_ref="clearance:crash",
        effect_name="crash-effect",
    )
    recovery = inspect_recovery(journal=journal, permit_store=store, permit_ref=permit)
    assert recovery.classification is RecoveryClassification.NOT_STARTED
    assert recovery.state is JournalState.INTENT_OPEN


def test_consumed_intent_is_conservatively_indeterminate(tmp_path: Path) -> None:
    store = SQLitePermitStore(tmp_path / "permits.sqlite3")
    journal = SQLiteExecutionJournal(tmp_path / "journal.sqlite3")
    permit = "permit:consumed-intent"
    assert journal.open_intent(
        permit_ref=permit,
        action_digest=_digest(_action()),
        execution_context_hash=_digest(_context(_action())),
        clearance_ref="clearance:crash",
        effect_name="crash-effect",
    )
    assert store.consume_once(permit)
    recovery = inspect_recovery(journal=journal, permit_store=store, permit_ref=permit)
    assert recovery.classification is RecoveryClassification.INDETERMINATE_EFFECT


def test_hard_crash_inside_effect_is_indeterminate_and_never_replayed(tmp_path: Path) -> None:
    permit_db = tmp_path / "permits.sqlite3"
    journal_db = tmp_path / "journal.sqlite3"
    marker = tmp_path / "effect.marker"
    permit = "permit:effect-crash"
    process = _process_context().Process(
        target=_hard_exit_from_effect,
        args=(str(permit_db), str(journal_db), str(marker), permit),
    )
    process.start()
    process.join(timeout=20)
    assert process.exitcode == 73
    assert marker.read_text(encoding="utf-8").splitlines() == ["EFFECT"]

    store = SQLitePermitStore(permit_db)
    journal = SQLiteExecutionJournal(journal_db)
    recovery = inspect_recovery(journal=journal, permit_store=store, permit_ref=permit)
    assert recovery.classification is RecoveryClassification.INDETERMINATE_EFFECT
    assert recovery.state is JournalState.EFFECT_INVOKING
    assert store.is_consumed(permit) is True

    restarted = EffectBoundary(
        store,
        evidence_sink=_ClosedSink(),
        execution_journal=journal,
    )
    replay_calls: list[str] = []
    with pytest.raises(ExecutionRecoveryRequired) as excinfo:
        restarted.commit(
            reht=_StaticReht(permit),
            context_factory=_context,
            action_contract=_action(),
            effect=BoundaryEffect.seal(
                "crash-effect",
                lambda _: replay_calls.append("REPLAY"),
            ),
        )
    assert excinfo.value.recovery.classification is RecoveryClassification.INDETERMINATE_EFFECT
    assert replay_calls == []
    assert marker.read_text(encoding="utf-8").splitlines() == ["EFFECT"]


def test_receipt_ready_crash_allows_evidence_only_reconciliation(tmp_path: Path) -> None:
    permit_db = tmp_path / "permits.sqlite3"
    journal_db = tmp_path / "journal.sqlite3"
    marker = tmp_path / "effect.marker"
    permit = "permit:receipt-ready"
    process = _process_context().Process(
        target=_hard_exit_after_receipt_ready,
        args=(str(permit_db), str(journal_db), str(marker), permit),
    )
    process.start()
    process.join(timeout=20)
    assert process.exitcode == 74

    store = SQLitePermitStore(permit_db)
    journal = SQLiteExecutionJournal(journal_db)
    recovery = inspect_recovery(journal=journal, permit_store=store, permit_ref=permit)
    assert recovery.classification is RecoveryClassification.READY_FOR_EVIDENCE_CLOSURE
    assert recovery.receipt is not None

    events: list[str] = []
    closure = reconcile_receipt_ready(
        journal=journal,
        evidence_sink=_ClosedSink(events),
        permit_ref=permit,
    )
    assert closure.closed is True
    assert len(events) == 1
    assert marker.read_text(encoding="utf-8").splitlines() == ["EFFECT"]
    after = inspect_recovery(journal=journal, permit_store=store, permit_ref=permit)
    assert after.classification is RecoveryClassification.CLOSED


def test_evidence_closing_crash_stays_indeterminate_and_is_not_auto_retried(tmp_path: Path) -> None:
    permit_db = tmp_path / "permits.sqlite3"
    journal_db = tmp_path / "journal.sqlite3"
    permit = "permit:evidence-closing"
    process = _process_context().Process(
        target=_hard_exit_during_evidence_closing,
        args=(str(permit_db), str(journal_db), permit),
    )
    process.start()
    process.join(timeout=20)
    assert process.exitcode == 75

    store = SQLitePermitStore(permit_db)
    journal = SQLiteExecutionJournal(journal_db)
    recovery = inspect_recovery(journal=journal, permit_store=store, permit_ref=permit)
    assert recovery.classification is RecoveryClassification.INDETERMINATE_EVIDENCE_CLOSURE
    assert recovery.state is JournalState.EVIDENCE_CLOSING

    events: list[str] = []
    with pytest.raises(ExecutionJournalError, match="only RECEIPT_READY"):
        reconcile_receipt_ready(
            journal=journal,
            evidence_sink=_ClosedSink(events),
            permit_ref=permit,
        )
    assert events == []


def test_duplicate_intent_never_reopens_execution(tmp_path: Path) -> None:
    journal = SQLiteExecutionJournal(tmp_path / "journal.sqlite3")
    kwargs = {
        "permit_ref": "permit:duplicate",
        "action_digest": _digest(_action()),
        "execution_context_hash": _digest(_context(_action())),
        "clearance_ref": "clearance:crash",
        "effect_name": "crash-effect",
    }
    assert journal.open_intent(**kwargs) is True
    assert journal.open_intent(**kwargs) is False


def test_closed_entries_leave_unresolved_scan(tmp_path: Path) -> None:
    store = SQLitePermitStore(tmp_path / "permits.sqlite3")
    journal = SQLiteExecutionJournal(tmp_path / "journal.sqlite3")
    permit = "permit:closed"
    assert journal.open_intent(
        permit_ref=permit,
        action_digest=_digest(_action()),
        execution_context_hash=_digest(_context(_action())),
        clearance_ref="clearance:crash",
        effect_name="crash-effect",
    )
    assert store.consume_once(permit)
    journal.mark_effect_invoking(permit)
    journal.mark_receipt_ready(permit, _receipt(permit))
    reconcile_receipt_ready(
        journal=journal,
        evidence_sink=_ClosedSink(),
        permit_ref=permit,
    )
    assert journal.list_unresolved() == ()
