"""CPU-only falsification of multi-host persistence assumptions.

This probe intentionally gives two simulated hosts independent SQLite stores. It
confirms that same-host SQLite durability does not provide cross-host single-use
truth, then verifies that EffectBoundary refuses to call that configuration
MULTI_HOST production.
"""

from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path

from valo_reht.consistency import DeploymentTopology
from valo_reht.durable_permit_store import SQLitePermitStore
from valo_reht.effect_boundary import EffectBoundary
from valo_reht.execution_journal import SQLiteExecutionJournal
from valo_reht.runtime_interlocks import canonical_digest


class _UnusedEvidenceSink:
    def close(self, receipt):
        raise AssertionError("split-brain construction probe must not execute")


def _open_intent(journal: SQLiteExecutionJournal, permit_ref: str, index: int) -> bool:
    return journal.open_intent(
        permit_ref=permit_ref,
        action_digest=canonical_digest({"action_id": f"action:{index}"}),
        execution_context_hash=canonical_digest({"state_version": 1}),
        clearance_ref=f"clearance:{index}",
        effect_name="split-brain-effect",
    )


def run(attempts: int) -> dict[str, object]:
    if attempts < 1:
        raise ValueError("attempts must be positive")
    started = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix="valo-reht-split-brain-") as root:
        base = Path(root)
        permit_a = SQLitePermitStore(base / "host-a-permits.sqlite3")
        permit_b = SQLitePermitStore(base / "host-b-permits.sqlite3")
        journal_a = SQLiteExecutionJournal(base / "host-a-journal.sqlite3")
        journal_b = SQLiteExecutionJournal(base / "host-b-journal.sqlite3")

        dual_permit_accepts = 0
        dual_intent_accepts = 0
        for index in range(attempts):
            permit_ref = f"permit:split-brain:{index}"
            if permit_a.consume_once(permit_ref) and permit_b.consume_once(permit_ref):
                dual_permit_accepts += 1

            intent_ref = f"permit:intent-split-brain:{index}"
            if _open_intent(journal_a, intent_ref, index) and _open_intent(
                journal_b, intent_ref, index
            ):
                dual_intent_accepts += 1

        gate_error = None
        try:
            EffectBoundary(
                SQLitePermitStore(base / "gate-permits.sqlite3"),
                evidence_sink=_UnusedEvidenceSink(),
                execution_journal=SQLiteExecutionJournal(base / "gate-journal.sqlite3"),
                deployment_topology=DeploymentTopology.MULTI_HOST,
            )
        except ValueError as exc:
            gate_error = str(exc)

    expected_limitation = (
        dual_permit_accepts == attempts and dual_intent_accepts == attempts
    )
    guard_present = bool(
        gate_error and "distributed-consensus permit store" in gate_error
    )
    return {
        "schema": "valo.reht.multi-host-split-brain-falsification.v1",
        "attempts": attempts,
        "cpu_only": True,
        "external_api_cost": 0,
        "dual_permit_accepts": dual_permit_accepts,
        "dual_intent_accepts": dual_intent_accepts,
        "sqlite_split_brain_limitation_confirmed": expected_limitation,
        "multi_host_same_host_store_guard_present": guard_present,
        "gate_error": gate_error,
        "distributed_consensus_backend_verified": False,
        "classification": (
            "LIMITATION_CONFIRMED_AND_GUARD_PRESENT"
            if expected_limitation and guard_present
            else "FAIL"
        ),
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempts", type=int, default=1000)
    parser.add_argument(
        "--output",
        default="validation/results/multi_host_split_brain.json",
    )
    args = parser.parse_args()
    payload = run(args.attempts)
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(rendered + "\n", encoding="utf-8")
    if payload["classification"] == "FAIL":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
