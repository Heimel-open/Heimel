"""
Canonical Memory (#139) — structured, queryable memory store.

Stores user profile, work context, decisions, and policies.
NOT a chat-log dump. Each MemoryRecord carries type, content,
provenance, timestamp, and optional TTL for automatic expiry.

Design:
  - JSONL-backed append-only store (simple, deterministic, no hidden state).
  - In-memory index built on load for fast query by type/provenance.
  - TTL expiry checked on every query; expired records are logically removed.
  - Provenance tracks the source system/agent that created the record.

Canonical rules:
  - C0/α/τ are env vars only, never hardcoded.
  - Deterministic, synchronous, no hidden state.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional


class MemoryType(str, Enum):
    """Canonical memory types — NOT a chat-log taxonomy."""

    USER_PROFILE = "user_profile"
    WORK_CONTEXT = "work_context"
    DECISION = "decision"
    POLICY = "policy"
    GOVERNANCE_SIGNAL = "governance_signal"
    PROVENANCE_RECORD = "provenance_record"
    RELATION = "relation"
    CONSEQUENCE = "consequence"
    BELIEF = "belief"
    CONSOLIDATION = "consolidation"


# C0 / α / τ from env vars only — never hardcoded
_C0_LOW = float(os.environ.get("PAIOS_C0_LOW", "0.3"))
_C0_HIGH = float(os.environ.get("PAIOS_C0_HIGH", "0.7"))
_ALPHA = float(os.environ.get("PAIOS_ALPHA", "0.1"))
_TAU = float(os.environ.get("PAIOS_TAU", "3600"))


@dataclass
class MemoryRecord:
    """A single canonical memory entry.

    Fields:
        id:          Unique record identifier (UUID or application-defined).
        type:        MemoryType classifying this record.
        content:     Structured payload (dict or JSON-serialisable value).
        provenance:  Source system/agent that created this record.
        timestamp:   Unix epoch seconds when the record was created.
        ttl:         Time-to-live in seconds (None = no expiry).
    """

    id: str
    type: MemoryType
    content: Dict[str, Any]
    provenance: str
    timestamp: float = field(default_factory=time.time)
    ttl: Optional[float] = None
    confidence: Optional[float] = None
    support_refs: tuple[str, ...] = ()
    conflict_refs: tuple[str, ...] = ()

    def validate(self) -> tuple[str, ...]:
        errors: List[str] = []
        if not self.id.strip():
            errors.append("id is required")
        if not self.provenance.strip():
            errors.append("provenance is required")
        if self.confidence is not None and not 0.0 <= self.confidence <= 1.0:
            errors.append("confidence must be between 0 and 1")
        return tuple(errors)

    @property
    def expired(self) -> bool:
        """Check whether this record has exceeded its TTL."""
        if self.ttl is None:
            return False
        return (time.time() - self.timestamp) > self.ttl


class CanonicalMemory:
    """Append-only, JSONL-backed canonical memory store.

    Thread-safety: not guaranteed. Callers must serialise access.
    """

    def __init__(self, path: Optional[Path] = None) -> None:
        self._path = path or Path(
            os.environ.get("PAIOS_MEMORY_PATH", "~/.paios/memory.jsonl")
        ).expanduser()
        self._records: List[MemoryRecord] = []
        self._dirty: bool = False
        self._persisted_count: int = 0
        self._load()
        self._persisted_count = len(self._records)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def store(self, record: MemoryRecord) -> None:
        """Append a validated, uniquely identified record."""
        errors = record.validate()
        if errors:
            raise ValueError("; ".join(errors))
        if any(existing.id == record.id for existing in self._records):
            raise ValueError(f"duplicate memory id: {record.id}")
        self._records.append(record)
        self._dirty = True

    def query(
        self,
        *,
        type: Optional[MemoryType] = None,
        provenance: Optional[str] = None,
        limit: int = 100,
        include_expired: bool = False,
    ) -> List[MemoryRecord]:
        """Query records by type and/or provenance, newest-first.

        Expired records are excluded unless *include_expired* is True.
        """
        results: List[MemoryRecord] = []
        for rec in reversed(self._records):
            if not include_expired and rec.expired:
                continue
            if type is not None and rec.type != type:
                continue
            if provenance is not None and rec.provenance != provenance:
                continue
            results.append(rec)
            if len(results) >= limit:
                break
        return results

    def count(self) -> int:
        """Total stored records (including expired)."""
        return len(self._records)

    def flush(self) -> None:
        """Persist all records to disk (JSONL)."""
        if not self._dirty:
            return
        self._path.parent.mkdir(parents=True, exist_ok=True)
        new_records = self._records[self._persisted_count:]
        with open(self._path, "a") as f:
            for rec in new_records:
                f.write(json.dumps(asdict(rec)) + "\n")
        self._persisted_count = len(self._records)
        self._dirty = False

    def clear(self) -> None:
        """Forget the current view without rewriting canonical history."""
        self._records.clear()
        self._persisted_count = 0
        self._dirty = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load existing records from disk on startup."""
        if not self._path.exists():
            return
        with open(self._path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                data["type"] = MemoryType(data["type"])
                data["support_refs"] = tuple(data.get("support_refs", ()))
                data["conflict_refs"] = tuple(data.get("conflict_refs", ()))
                self._records.append(MemoryRecord(**data))
