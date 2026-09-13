"""Durable single-use permit consumption for EffectBoundary.

This module is subordinate mechanical enforcement. It cannot authorize an
action, mint a clearance, or widen authority. It only remembers that an
already-issued REHT permit has been consumed.

``SQLitePermitStore`` is a same-host durability/reference implementation. It is
safe across processes and process restarts that share the same local database
file. It is not a distributed consensus store and must not be presented as a
multi-host guarantee on filesystems without correct SQLite locking semantics.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from .consistency import ConsistencyScope


class PermitStoreUnavailable(RuntimeError):
    """Durable permit state could not be read or atomically updated."""


class SQLitePermitStore:
    """Atomic durable permit consumption backed by SQLite.

    Construction requires an explicit database path or ``VALO_REHT_PERMIT_DB``.
    There is intentionally no implicit temporary-file fallback for production.
    """

    production_safe = True
    consistency_scope = ConsistencyScope.SAME_HOST_SHARED

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        configured = path or os.environ.get("VALO_REHT_PERMIT_DB")
        if configured is None or not str(configured).strip():
            raise ValueError(
                "durable permit store requires path or VALO_REHT_PERMIT_DB"
            )
        self.path = Path(configured)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.path,
            timeout=10.0,
            isolation_level=None,
        )
        connection.execute("PRAGMA busy_timeout=10000")
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=FULL")
        return connection

    def _initialize(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS consumed_permits (
                        permit_ref TEXT PRIMARY KEY,
                        consumed_at TEXT NOT NULL
                    )
                    """
                )
        except sqlite3.Error as exc:
            raise PermitStoreUnavailable(
                f"permit store initialization failed: {exc}"
            ) from exc

    def consume_once(self, permit_ref: str) -> bool:
        """Atomically persist the first consumption of ``permit_ref``."""
        if not isinstance(permit_ref, str) or not permit_ref:
            raise PermitStoreUnavailable("permit_ref is required")
        consumed_at = datetime.now(UTC).isoformat().replace("+00:00", "Z")
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                try:
                    connection.execute(
                        """
                        INSERT INTO consumed_permits (permit_ref, consumed_at)
                        VALUES (?, ?)
                        """,
                        (permit_ref, consumed_at),
                    )
                except sqlite3.IntegrityError:
                    connection.rollback()
                    return False
                connection.commit()
                return True
        except sqlite3.Error as exc:
            raise PermitStoreUnavailable(
                f"permit store consume failed: {exc}"
            ) from exc

    def is_consumed(self, permit_ref: str) -> bool:
        """Return whether the permit has a durable consumption record."""
        if not isinstance(permit_ref, str) or not permit_ref:
            raise PermitStoreUnavailable("permit_ref is required")
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT 1 FROM consumed_permits WHERE permit_ref = ?",
                    (permit_ref,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise PermitStoreUnavailable(
                f"permit store read failed: {exc}"
            ) from exc
        return row is not None


__all__ = ["PermitStoreUnavailable", "SQLitePermitStore"]
