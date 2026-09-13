"""Crash/restart falsification for the durable REHT permit store.

CPU-only. No model, network, GPU, or external API calls are required. The probe
attacks restart persistence, transaction atomicity, and cross-process replay.
It does not claim distributed multi-host safety.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
import time
from collections import Counter
from multiprocessing import get_context
from pathlib import Path
from typing import Any

from valo_reht.durable_permit_store import SQLitePermitStore

DEFAULT_SEED = 20260826
DEFAULT_WORKERS = 8
DEFAULT_RACE_PERMITS = 100
DEFAULT_CRASH_CYCLES = 8


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


def run(
    *,
    workers: int = DEFAULT_WORKERS,
    race_permits: int = DEFAULT_RACE_PERMITS,
    crash_cycles: int = DEFAULT_CRASH_CYCLES,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    started = time.perf_counter()
    context = get_context("spawn")
    with tempfile.TemporaryDirectory(prefix="valo-reht-crash-") as directory:
        root = Path(directory)
        db_path = root / "permits.sqlite3"
        store = SQLitePermitStore(db_path)

        restart_failures = 0
        for index in range(race_permits):
            permit = f"permit:restart:{seed}:{index}"
            if not store.consume_once(permit):
                restart_failures += 1
            if SQLitePermitStore(db_path).consume_once(permit):
                restart_failures += 1

        committed_crash_failures = 0
        for index in range(crash_cycles):
            permit = f"permit:committed-crash:{seed}:{index}"
            marker = root / f"committed-{index}.marker"
            process = context.Process(
                target=_consume_then_hard_exit,
                args=(str(db_path), permit, str(marker)),
            )
            process.start()
            process.join(timeout=20)
            if process.exitcode != 71 or not marker.exists():
                committed_crash_failures += 1
                continue
            if marker.read_text(encoding="utf-8") != "True":
                committed_crash_failures += 1
            if SQLitePermitStore(db_path).consume_once(permit):
                committed_crash_failures += 1

        rollback_failures = 0
        for index in range(crash_cycles):
            permit = f"permit:uncommitted-crash:{seed}:{index}"
            marker = root / f"uncommitted-{index}.marker"
            process = context.Process(
                target=_insert_without_commit_then_hard_exit,
                args=(str(db_path), permit, str(marker)),
            )
            process.start()
            process.join(timeout=20)
            if process.exitcode != 72 or not marker.exists():
                rollback_failures += 1
                continue
            if not SQLitePermitStore(db_path).consume_once(permit):
                rollback_failures += 1

        permits = tuple(f"permit:race:{seed}:{index}" for index in range(race_permits))
        with context.Pool(workers) as pool:
            wins = pool.map(
                _race_worker,
                [
                    (
                        str(db_path),
                        permits,
                        (index * 17) % len(permits),
                    )
                    for index in range(workers)
                ],
            )
        counts = Counter(permit for worker_wins in wins for permit in worker_wins)
        duplicate_consumptions = sum(max(0, count - 1) for count in counts.values())
        permits_without_winner = len(set(permits) - set(counts))

    failures = (
        restart_failures
        + committed_crash_failures
        + rollback_failures
        + duplicate_consumptions
        + permits_without_winner
    )
    return {
        "schema": "valo.reht.crash-restart-permit-falsification.v1",
        "seed": seed,
        "classification": "PASS" if failures == 0 else "FAIL",
        "scope": "same-host shared SQLite database; not multi-host distributed consensus",
        "cpu_only": True,
        "external_api_cost": 0,
        "restart_persistence": {
            "permits": race_permits,
            "failures": restart_failures,
        },
        "hard_crash_after_committed_consume": {
            "cycles": crash_cycles,
            "failures": committed_crash_failures,
        },
        "hard_crash_before_commit": {
            "cycles": crash_cycles,
            "rollback_failures": rollback_failures,
        },
        "cross_process_race": {
            "workers": workers,
            "permits": race_permits,
            "attempts": workers * race_permits,
            "duplicate_consumptions": duplicate_consumptions,
            "permits_without_winner": permits_without_winner,
        },
        "elapsed_seconds": round(time.perf_counter() - started, 6),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS)
    parser.add_argument("--race-permits", type=int, default=DEFAULT_RACE_PERMITS)
    parser.add_argument("--crash-cycles", type=int, default=DEFAULT_CRASH_CYCLES)
    parser.add_argument("--seed", type=int, default=DEFAULT_SEED)
    parser.add_argument("--output")
    args = parser.parse_args()
    if not 2 <= args.workers <= 32:
        raise SystemExit("workers must be between 2 and 32")
    if args.race_permits < 1 or args.crash_cycles < 1:
        raise SystemExit("race-permits and crash-cycles must be positive")
    payload = run(
        workers=args.workers,
        race_permits=args.race_permits,
        crash_cycles=args.crash_cycles,
        seed=args.seed,
    )
    rendered = json.dumps(payload, indent=2, sort_keys=True)
    print(rendered)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    if payload["classification"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
