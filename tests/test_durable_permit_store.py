from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections import Counter
from multiprocessing import get_all_start_methods, get_context
from pathlib import Path
from typing import Any

import pytest

from valo_reht.contracts import DecisionResult
from valo_reht.durable_permit_store import SQLitePermitStore
from valo_reht.effect_boundary import EffectBoundary
from valo_reht.evidence_closure import EvidenceClosure
from valo_reht.execution_journal import (
    ExecutionRecoveryRequired,
    RecoveryClassification,
    SQLiteExecutionJournal,
)
from valo_reht.runtime_interlocks import BoundaryEffect


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _process_context():
    method = "fork" if "fork" in get_all_start_methods() else "spawn"
    return get_context(method)


def _durable_marker(path: str, value: str) -> None:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(value)
        handle.flush()
        os.fsync(handle.fileno())


def _consume_then_hard_exit(db_path: str, permit_ref: str, marker: str) -> None:
    store = SQLitePermitStore(db_path)
    consumed = store.consume_once(permit_ref)
    _durable_marker(marker, str(consumed))
    os._exit(71)


def _insert_without_commit_then_hard_exit(
    db_path: str,
    permit_ref: str,
    marker: str,
) -> None:
    connection = sqlite3.connect(db_path, timeout=10.0, isolation_level=None)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("BEGIN IMMEDIATE")
    connection.execute(
        "INSERT INTO consumed_permits (permit_ref, consumed_at) VALUES (?, ?)",
        (permit_ref, "uncommitted"),
    )
    _durable_marker(marker, "inserted")
    os._exit(72)


def _race_worker(args: tuple[str, tuple[str, ...], int]) -> tuple[str, ...]:
    db_path, permits, offset = args
    store = SQLitePermitStore(db_path)
    sequence = permits[offset:] + permits[:offset]
    return tuple(permit for permit in sequence if store.consume_once(permit))


class _SamePermitReht:
    def __init__(self, permit_ref: str) -> None:
        self.permit_ref = permit_ref

    def authorize(
        self,
        execution_context: dict[str, Any],
        action_contract: dict[str, Any],
    ) -> DecisionResult:
        return DecisionResult(
            decision="ALLOW",
            clearance_ref="clearance:durable",
            permit_ref=self.permit_ref,
            execution_context_hash=_digest(execution_context),
        )


class _ClosedEvidenceSink:
    def close(self, receipt: Any) -> EvidenceClosure:
        return EvidenceClosure(
            receipt_id=receipt.receipt_id,
            veritas_ref=f"veritas-worm:{receipt.receipt_id}",
            kernel_ref=f"kernel:{receipt.receipt_id}",
            closed=True,
        )


def test_store_requires_explicit_path_or_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VALO_REHT_PERMIT_DB", raising=False)
    with pytest.raises(ValueError, match="requires path"):
        SQLitePermitStore()


def test_restart_does_not_rearm_consumed_permit(tmp_path: Path) -> None:
    db_path = tmp_path / "permits.sqlite3"
    assert SQLitePermitStore(db_path).consume_once("permit:restart") is True
    restarted = SQLitePermitStore(db_path)
    assert restarted.is_consumed("permit:restart") is True
    assert restarted.consume_once("permit:restart") is False


def test_hard_exit_after_committed_consume_stays_consumed(tmp_path: Path) -> None:
    db_path = tmp_path / "permits.sqlite3"
    SQLitePermitStore(db_path)
    marker = tmp_path / "committed.marker"
    process = _process_context().Process(
        target=_consume_then_hard_exit,
        args=(str(db_path), "permit:hard-exit", str(marker)),
    )
    process.start()
    process.join(timeout=20)
    assert process.exitcode == 71
    assert marker.read_text(encoding="utf-8") == "True"
    assert SQLitePermitStore(db_path).consume_once("permit:hard-exit") is False


def test_hard_exit_before_transaction_commit_rolls_back(tmp_path: Path) -> None:
    db_path = tmp_path / "permits.sqlite3"
    SQLitePermitStore(db_path)
    marker = tmp_path / "uncommitted.marker"
    process = _process_context().Process(
        target=_insert_without_commit_then_hard_exit,
        args=(str(db_path), "permit:uncommitted", str(marker)),
    )
    process.start()
    process.join(timeout=20)
    assert process.exitcode == 72
    assert marker.read_text(encoding="utf-8") == "inserted"
    assert SQLitePermitStore(db_path).consume_once("permit:uncommitted") is True


def test_multiple_processes_share_one_single_use_truth(tmp_path: Path) -> None:
    db_path = tmp_path / "permits.sqlite3"
    SQLitePermitStore(db_path)
    permits = tuple(f"permit:race:{index}" for index in range(24))
    context = _process_context()
    with context.Pool(4) as pool:
        wins = pool.map(
            _race_worker,
            [(str(db_path), permits, (index * 5) % len(permits)) for index in range(4)],
        )
    counts = Counter(permit for worker_wins in wins for permit in worker_wins)
    assert set(counts) == set(permits)
    assert all(count == 1 for count in counts.values())


def test_effect_boundary_restart_never_replays_closed_effect(tmp_path: Path) -> None:
    db_path = tmp_path / "permits.sqlite3"
    journal_path = tmp_path / "execution-journal.sqlite3"
    action = {"action_id": "action:durable", "action_type": "WRITE"}
    context = {"state_version": 1, "actor_id": "actor:1"}
    effect_calls: list[str] = []
    effect = BoundaryEffect.seal(
        "durable-effect",
        lambda exact_action: effect_calls.append(exact_action["action_id"]) or {"ok": True},
    )
    reht = _SamePermitReht("permit:boundary-restart")

    first = EffectBoundary(
        SQLitePermitStore(db_path),
        evidence_sink=_ClosedEvidenceSink(),
        execution_journal=SQLiteExecutionJournal(journal_path),
    )
    result = first.commit(
        reht=reht,
        context_factory=lambda _: context,
        action_contract=action,
        effect=effect,
    )
    assert result.effect_committed is True
    assert result.valid_completion is True

    restarted = EffectBoundary(
        SQLitePermitStore(db_path),
        evidence_sink=_ClosedEvidenceSink(),
        execution_journal=SQLiteExecutionJournal(journal_path),
    )
    with pytest.raises(ExecutionRecoveryRequired) as excinfo:
        restarted.commit(
            reht=reht,
            context_factory=lambda _: context,
            action_contract=action,
            effect=effect,
        )
    assert excinfo.value.recovery.classification is RecoveryClassification.CLOSED
    assert effect_calls == ["action:durable"]
