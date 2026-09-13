"""
VAIG Embedded — SQLite WORM Log
Canonical on-device WORM log for vaig.vaig_embedded. SHA-256 hash chained,
append-only. Use ``:memory:`` for in-process runtimes or a file path for
durable logging.
"""
import sqlite3
import hashlib
import json
import time

class SQLiteWORM:
    """Canonical WORM log using SQLite. SHA-256 hash chained."""

    def __init__(self, db_path: str = "vaig_worm.db"):
        self.db_path = db_path
        self._conn = sqlite3.connect(db_path)
        self._init_table()

    def _init_table(self):
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS worm_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                sequence INTEGER NOT NULL,
                prev_hash TEXT NOT NULL,
                entry_hash TEXT NOT NULL,
                source_id TEXT,
                distrust_level INTEGER,
                action TEXT,
                score REAL,
                metadata TEXT
            )
        """)
        self._conn.commit()

    def append(self, source_id: str = "embedded", distrust_level: int = 0,
               action: str = "PASS", score: float = 0.0, metadata: dict = None):
        prev = self._last_hash()
        seq = self._next_sequence()
        payload = {
            "timestamp": time.time(),
            "sequence": seq,
            "prev_hash": prev,
            "source_id": source_id,
            "distrust_level": distrust_level,
            "action": action,
            "score": score,
            "metadata": json.dumps(metadata or {}),
        }
        entry_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

        self._conn.execute(
            "INSERT INTO worm_log VALUES (NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (payload["timestamp"], seq, prev, entry_hash, source_id,
             distrust_level, action, score, payload["metadata"])
        )
        self._conn.commit()
        return entry_hash

    def _last_hash(self) -> str:
        row = self._conn.execute(
            "SELECT entry_hash FROM worm_log ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return row[0] if row else "0" * 64

    def _next_sequence(self) -> int:
        row = self._conn.execute(
            "SELECT MAX(sequence) FROM worm_log"
        ).fetchone()
        return (row[0] or -1) + 1

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) FROM worm_log").fetchone()
        return row[0] if row else 0

    def verify(self) -> bool:
        rows = self._conn.execute(
            "SELECT timestamp, sequence, prev_hash, entry_hash, source_id, "
            "distrust_level, action, score, metadata FROM worm_log ORDER BY id"
        ).fetchall()
        prev = "0" * 64
        for row in rows:
            payload = {
                "timestamp": row[0], "sequence": row[1], "prev_hash": row[2],
                "source_id": row[4], "distrust_level": row[5],
                "action": row[6], "score": row[7], "metadata": row[8],
            }
            expected = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
            if row[3] != expected or row[2] != prev:
                return False
            prev = row[3]
        return True

    def close(self):
        """Close the underlying SQLite connection."""
        self._conn.close()
