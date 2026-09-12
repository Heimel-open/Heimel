from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Self

from ..contracts.events import CanonicalEvent
from ..world.state import WorldState
from .base import AppendOnlyStore


class SQLiteStore(AppendOnlyStore):
    """Persistent append-only Kernel store backed by SQLite.

    Each committed event row carries the post-event WorldState snapshot. The
    event stream remains the audit/replay source; the stored snapshot is a
    restart accelerator, not a second authority source.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._connection = sqlite3.connect(str(self.path))
        self._connection.execute("PRAGMA journal_mode=WAL")
        self._connection.execute("PRAGMA synchronous=FULL")
        self._connection.execute("PRAGMA foreign_keys=ON")
        self._initialize()

    def _initialize(self) -> None:
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS kernel_events (
                sequence INTEGER PRIMARY KEY,
                event_id TEXT NOT NULL UNIQUE,
                idempotency_key TEXT UNIQUE,
                event_json TEXT NOT NULL,
                state_json TEXT NOT NULL
            )
            """
        )
        self._connection.commit()

    def append_event(self, event: CanonicalEvent, state: WorldState) -> None:
        if event.sequence is None or event.sequence < 1:
            raise ValueError("sealed event sequence is required")
        expected = self._connection.execute(
            "SELECT COALESCE(MAX(sequence), 0) + 1 FROM kernel_events"
        ).fetchone()[0]
        if event.sequence != expected:
            raise ValueError(
                f"event sequence {event.sequence} does not match expected {expected}"
            )
        try:
            with self._connection:
                self._connection.execute(
                    """
                    INSERT INTO kernel_events(
                        sequence, event_id, idempotency_key, event_json, state_json
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        event.sequence,
                        event.event_id,
                        event.idempotency_key,
                        event.model_dump_json(),
                        state.model_dump_json(),
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("duplicate event or idempotency key") from exc

    def events(self) -> list[CanonicalEvent]:
        rows = self._connection.execute(
            "SELECT event_json FROM kernel_events ORDER BY sequence"
        ).fetchall()
        return [CanonicalEvent.model_validate_json(row[0]) for row in rows]

    def last_event(self) -> CanonicalEvent | None:
        row = self._connection.execute(
            "SELECT event_json FROM kernel_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return CanonicalEvent.model_validate_json(row[0])

    def state(self) -> WorldState | None:
        row = self._connection.execute(
            "SELECT state_json FROM kernel_events ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return WorldState.model_validate_json(row[0])

    def has_idempotency_key(self, key: str) -> bool:
        row = self._connection.execute(
            "SELECT 1 FROM kernel_events WHERE idempotency_key = ? LIMIT 1",
            (key,),
        ).fetchone()
        return row is not None

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

