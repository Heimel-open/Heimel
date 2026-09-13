"""Durable append-only JSONL archive for Veritas Edge V1."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterable, List

from valo_edge.governance.canonical import canonical_bytes
from valo_edge.veritas.contracts_v1 import (
    VERITAS_GENESIS_DIGEST,
    VeritasChainEntryV1,
)


def verify_chain_entries(
    entries: Iterable[VeritasChainEntryV1],
    *,
    starting_previous_digest: str = VERITAS_GENESIS_DIGEST,
    starting_sequence: int = 0,
) -> bool:
    """Verify sequence, payload digests and hash-chain continuity."""

    previous = starting_previous_digest
    expected_sequence = starting_sequence
    for entry in entries:
        if entry.sequence != expected_sequence:
            return False
        if entry.previous_entry_digest != previous:
            return False
        if entry.record.payload_digest != _payload_digest(entry.record.payload):
            return False
        if entry.entry_digest is None or entry.entry_digest != entry.compute_digest():
            return False
        previous = entry.entry_digest
        expected_sequence += 1
    return True


def _payload_digest(payload: object) -> str:
    from valo_edge.contracts import sha256_digest

    return sha256_digest(payload)


class VeritasJsonlArchiveV1:
    """Append-only durable archive.

    The API intentionally exposes no update or delete operation. Existing lines
    are verified before the archive is accepted, and every append is fsync'd.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._entries: List[VeritasChainEntryV1] = self._load()
        if not verify_chain_entries(self._entries):
            raise ValueError("Veritas archive integrity verification failed")

    def _load(self) -> List[VeritasChainEntryV1]:
        if not self.path.exists():
            return []
        entries: List[VeritasChainEntryV1] = []
        with self.path.open("rb") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                if not raw_line.strip():
                    raise ValueError(f"blank archive line at {line_number}")
                try:
                    payload = json.loads(raw_line.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                    raise ValueError(f"invalid archive line at {line_number}") from exc
                if not isinstance(payload, dict) or "entry_digest" not in payload:
                    raise ValueError(f"incomplete archive line at {line_number}")
                record = payload.get("record")
                if not isinstance(record, dict) or "payload_digest" not in record:
                    raise ValueError(f"missing record digest at {line_number}")
                entries.append(VeritasChainEntryV1.model_validate(payload))
        return entries

    def append(self, entry: VeritasChainEntryV1) -> None:
        expected_sequence = len(self._entries)
        expected_previous = (
            self._entries[-1].entry_digest if self._entries else VERITAS_GENESIS_DIGEST
        )
        if entry.sequence != expected_sequence:
            raise ValueError("archive sequence mismatch")
        if entry.previous_entry_digest != expected_previous:
            raise ValueError("archive previous digest mismatch")
        if not verify_chain_entries(
            [entry],
            starting_previous_digest=expected_previous,
            starting_sequence=expected_sequence,
        ):
            raise ValueError("entry integrity verification failed")

        encoded = canonical_bytes(entry.model_dump(mode="json", exclude_none=True)) + b"\n"
        with self.path.open("ab") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        self._entries.append(entry.model_copy(deep=True))

    def read_all(self) -> List[VeritasChainEntryV1]:
        return [entry.model_copy(deep=True) for entry in self._entries]

    @property
    def tail_digest(self) -> str:
        if not self._entries:
            return VERITAS_GENESIS_DIGEST
        assert self._entries[-1].entry_digest is not None
        return self._entries[-1].entry_digest

    @property
    def next_sequence(self) -> int:
        return len(self._entries)

    def verify(self) -> bool:
        return verify_chain_entries(self._entries)


__all__ = ["VeritasJsonlArchiveV1", "verify_chain_entries"]
