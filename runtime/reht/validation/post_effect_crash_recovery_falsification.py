"""CPU-only falsification of post-effect crash recovery semantics.

The harness kills worker processes at consequence-sensitive points and verifies
that restart never replays an external effect merely because evidence was
incomplete. No model, network, GPU, or external API calls are required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
import tempfile
import time
from multiprocessing import get_all_start_methods, get_context
from pathlib import Path
from typing import Any

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
from valo_reht.runtime_interlocks import build_execution_receipt, canonical_digest

DEFAULT_CYCLES = 100
DEFAULT_SEED = 20260826


def _process_context():
    method = "fork" if "fork" in get_all_start_methods() else "spawn"
    return get_context(method)


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def _action(index: int) -> dict[str, Any]:
    return {
        "action_id": f"action:crash:{index}",
        "action_type": "WRITE",
        "target": "target:1",
        "payload": {"index": index},
    }


def _context(_: dict[str, Any]) -> dict[str, Any]:
    return {"state_version": 1, "actor_id": "actor:1"}


class StaticReht:
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


class ClosedSink:
    def close(self, receipt) -> EvidenceClosure:
        return EvidenceClosure(
            receipt_id=receipt.receipt_id,
            veritas_ref=f"veritas-worm:{receipt.receipt_id}",
            kernel_ref=f"kernel:{receipt.receipt_id}",
            closed=True,
        )


def _append_marker(path: str, marker: str) -> None:
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(marker + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _receipt(index: int, permit_ref: str):
    action = _action(index)
    return build_execution_receipt(
        status="COMMITTED",
        action=action,
        execution_context_hash=_digest(_context(action)),
        reht_decision="ALLOW",
        clearance_ref="clearance:crash",
        permit_ref=permit_ref,
        effect_name="crash-effect",
        effect_result={"ok": True, "index": index},
    )


def _crash_inside_effect(
    permit_db: str,
    journal_db: str,
    marker_path: str,
    permit_ref: str,
    index: int,
) -> None:
    boundary = EffectBoundary(
        SQLitePermitStore(permit_db),
        evidence_sink=ClosedSink(),
        execution_journal=SQLiteExecutionJournal(journal_db),
    )

    def effect(_: dict[str, Any]) -> None:
        _append_marker(marker_path, permit_ref)
        os._exit(73)

    boundary.commit(
        reht=StaticReht(permit_ref),
        context_factory=_context,
        action_contract=_action(index),
        effect=BoundaryEffect.seal("crash-effect", effect),
    )
    os._exit(99)


def _crash_receipt_ready(
    permit_db: str,
    journal_db: str,
    marker_path: str,
    permit_ref: str,
    index: int,
) -> None:
    store = SQLitePermitStore(permit_db)
    journal = SQLiteExecutionJournal(journal_db)
    action = _action(index)
    assert journal.open_intent(
        permit_ref=permit_ref,
        action_digest=canonical_digest(action),
        execution_context_hash=_digest(_context(action)),
        clearance_ref="clearance:crash",
        effect_name="crash-effect",
    )
    assert store.consume_once(permit_ref)
    journal.mark_effect_invoking(permit_ref)
    _append_marker(marker_path, permit_ref)
    journal.mark_receipt_ready(permit_ref, _receipt(index, permit_ref))
    os._exit(74)


def _crash_evidence_closing(
    permit_db: str,
    journal_db: str,
    permit_ref: str,
    index: int,
) -> None:
    store = SQLitePermitStore(permit_db)
    journal = SQLiteExecutionJournal(journal_db)
    action = _action(index)
    assert journal.open_intent(
        permit_ref=permit_ref,
        action_digest=canonical_digest(action),
        execution_context_hash=_digest(_context(action)),
        clearance_ref="clearance:crash",
        effect_name="crash-effect",
    )
    assert store.consume_once(permit_ref)
    journal.mark_effect_invoking(permit_ref)
    journal.mark_receipt_ready(permit_ref, _receipt(index, permit_ref))
    journal.mark_evidence_closing(permit_ref)
    os._exit(75)


def run(*, cycles: int, seed: int) -> dict[str, Any]:
    started = time.perf_counter()
    process_context = _process_context()
    failures: list[dict[str, Any]] = []
    counters = {
        "effect_crash_indeterminate": 0,
        "effect_replays": 0,
        "receipt_ready_reconciled": 0,
        "evidence_closing_indeterminate": 0,
        "closed_replays_blocked": 0,
    }

    with tempfile.TemporaryDirectory(prefix="valo-reht-post-effect-") as directory:
        root = Path(directory)
        permit_db = root / "permits.sqlite3"
        journal_db = root / "journal.sqlite3"
        marker = root / "effects.marker"
        store = SQLitePermitStore(permit_db)
        journal = SQLiteExecutionJournal(journal_db)

        for index in range(cycles):
            permit = f"permit:effect-crash:{seed}:{index}"
            process = process_context.Process(
                target=_crash_inside_effect,
                args=(str(permit_db), str(journal_db), str(marker), permit, index),
            )
            process.start()
            process.join(timeout=20)
            if process.exitcode != 73:
                failures.append({"family": "effect_crash", "index": index, "exitcode": process.exitcode})
                continue
            recovery = inspect_recovery(journal=journal, permit_store=store, permit_ref=permit)
            if recovery.classification is not RecoveryClassification.INDETERMINATE_EFFECT:
                failures.append(
                    {
                        "family": "effect_crash",
                        "index": index,
                        "classification": recovery.classification.value,
                    }
                )
                continue
            counters["effect_crash_indeterminate"] += 1
            replay_calls: list[str] = []
            restarted = EffectBoundary(
                store,
                evidence_sink=ClosedSink(),
                execution_journal=journal,
            )
            try:
                restarted.commit(
                    reht=StaticReht(permit),
                    context_factory=_context,
                    action_contract=_action(index),
                    effect=BoundaryEffect.seal(
                        "crash-effect",
                        lambda _: replay_calls.append("REPLAY"),
                    ),
                )
            except ExecutionRecoveryRequired:
                pass
            else:
                failures.append({"family": "effect_crash_replay", "index": index})
            counters["effect_replays"] += len(replay_calls)

        for index in range(cycles):
            permit = f"permit:receipt-ready:{seed}:{index}"
            process = process_context.Process(
                target=_crash_receipt_ready,
                args=(
                    str(permit_db),
                    str(journal_db),
                    str(marker),
                    permit,
                    cycles + index,
                ),
            )
            process.start()
            process.join(timeout=20)
            if process.exitcode != 74:
                failures.append({"family": "receipt_ready", "index": index, "exitcode": process.exitcode})
                continue
            recovery = inspect_recovery(journal=journal, permit_store=store, permit_ref=permit)
            if recovery.classification is not RecoveryClassification.READY_FOR_EVIDENCE_CLOSURE:
                failures.append(
                    {
                        "family": "receipt_ready",
                        "index": index,
                        "classification": recovery.classification.value,
                    }
                )
                continue
            closure = reconcile_receipt_ready(
                journal=journal,
                evidence_sink=ClosedSink(),
                permit_ref=permit,
            )
            if not closure.closed:
                failures.append({"family": "receipt_ready_closure", "index": index})
            else:
                counters["receipt_ready_reconciled"] += 1

        for index in range(cycles):
            permit = f"permit:evidence-closing:{seed}:{index}"
            process = process_context.Process(
                target=_crash_evidence_closing,
                args=(str(permit_db), str(journal_db), permit, 2 * cycles + index),
            )
            process.start()
            process.join(timeout=20)
            if process.exitcode != 75:
                failures.append({"family": "evidence_closing", "index": index, "exitcode": process.exitcode})
                continue
            recovery = inspect_recovery(journal=journal, permit_store=store, permit_ref=permit)
            if recovery.classification is not RecoveryClassification.INDETERMINATE_EVIDENCE_CLOSURE:
                failures.append(
                    {
                        "family": "evidence_closing",
                        "index": index,
                        "classification": recovery.classification.value,
                    }
                )
                continue
            try:
                reconcile_receipt_ready(
                    journal=journal,
                    evidence_sink=ClosedSink(),
                    permit_ref=permit,
                )
            except ExecutionJournalError:
                counters["evidence_closing_indeterminate"] += 1
            else:
                failures.append({"family": "evidence_closing_auto_retry", "index": index})

        for index in range(cycles):
            permit = f"permit:closed:{seed}:{index}"
            action = _action(3 * cycles + index)
            boundary = EffectBoundary(
                store,
                evidence_sink=ClosedSink(),
                execution_journal=journal,
            )
            calls: list[str] = []
            first = boundary.commit(
                reht=StaticReht(permit),
                context_factory=_context,
                action_contract=action,
                effect=BoundaryEffect.seal(
                    "crash-effect",
                    lambda _: calls.append("FIRST") or {"ok": True},
                ),
            )
            if not first.effect_committed:
                failures.append({"family": "closed_first", "index": index})
                continue
            try:
                boundary.commit(
                    reht=StaticReht(permit),
                    context_factory=_context,
                    action_contract=action,
                    effect=BoundaryEffect.seal(
                        "crash-effect",
                        lambda _: calls.append("REPLAY"),
                    ),
                )
            except ExecutionRecoveryRequired as exc:
                if exc.recovery.classification is RecoveryClassification.CLOSED:
                    counters["closed_replays_blocked"] += 1
                else:
                    failures.append(
                        {
                            "family": "closed_replay",
                            "index": index,
                            "classification": exc.recovery.classification.value,
                        }
                    )
            else:
                failures.append({"family": "closed_replay", "index": index, "error": "replay accepted"})
            if calls != ["FIRST"]:
                failures.append({"family": "closed_effect_count", "index": index, "calls": calls})

        marker_lines = marker.read_text(encoding="utf-8").splitlines() if marker.exists() else []

    if counters["effect_replays"] != 0:
        failures.append({"family": "aggregate", "effect_replays": counters["effect_replays"]})

    return {
        "schema": "valo.reht.post-effect-crash-recovery-falsification.v1",
        "seed": seed,
        "cycles_per_family": cycles,
        "classification": "PASS" if not failures else "FAIL",
        "cpu_only": True,
        "external_api_cost": 0,
        "python": sys.version,
        "platform": platform.platform(),
        "counters": counters,
        "durable_effect_markers": len(marker_lines),
        "failures": failures,
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles", type=int, default=DEFAULT_CYCLES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument(
        "--output",
        default="validation/results/post_effect_crash_recovery.json",
    )
    args = parser.parse_args()
    if args.cycles < 1:
        raise SystemExit("cycles must be positive")
    payload = run(cycles=args.cycles, seed=args.seed)
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    if payload["classification"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
