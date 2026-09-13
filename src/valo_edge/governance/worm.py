"""Embedded WORM log — append-only, hash-chained, stdlib-only.

On-device equivalent of the platform's WORM audit log. Every entry is bound
to the previous entry's hash, so any tampering breaks the chain and
``verify()`` fails closed. No external dependencies; suitable for micro
controllers and constrained runtimes.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, List, Optional

from valo_edge.governance.canonical import canonical_digest

GENESIS_HASH = "0" * 64


class WormEntry:
    """One immutable WORM entry."""

    __slots__ = ("sequence", "prev_hash", "payload", "entry_hash")

    def __init__(self, sequence: int, prev_hash: str, payload: Dict[str, Any]):
        self.sequence = sequence
        self.prev_hash = prev_hash
        self.payload = payload
        body = {
            "sequence": sequence,
            "prev_hash": prev_hash,
            "payload": payload,
        }
        self.entry_hash = canonical_digest(body)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sequence": self.sequence,
            "prev_hash": self.prev_hash,
            "payload": self.payload,
            "entry_hash": self.entry_hash,
        }


class WormLog:
    """Append-only hash-chained log. Fail-closed on tampering."""

    def __init__(self, tail_hash: str = GENESIS_HASH) -> None:
        self._tail_hash = tail_hash
        self._entries: List[WormEntry] = []

    def append(self, payload: Dict[str, Any]) -> WormEntry:
        entry = WormEntry(
            sequence=len(self._entries),
            prev_hash=self._tail_hash,
            payload=payload,
        )
        self._entries.append(entry)
        self._tail_hash = entry.entry_hash
        return entry

    @property
    def tail_hash(self) -> str:
        return self._tail_hash

    def last(self) -> Optional[WormEntry]:
        return self._entries[-1] if self._entries else None

    def read_all(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._entries]

    def count(self) -> int:
        return len(self._entries)

    def verify(self) -> bool:
        """Replay the chain and confirm integrity. Fail-closed."""
        prev = GENESIS_HASH
        for idx, entry in enumerate(self._entries):
            if entry.sequence != idx:
                return False
            if entry.prev_hash != prev:
                return False
            body = {
                "sequence": entry.sequence,
                "prev_hash": entry.prev_hash,
                "payload": entry.payload,
            }
            if canonical_digest(body) != entry.entry_hash:
                return False
            prev = entry.entry_hash
        return prev == self._tail_hash
