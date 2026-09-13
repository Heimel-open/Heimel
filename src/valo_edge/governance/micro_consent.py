"""Embedded micro-consent — immutable consent records, stdlib-only.

On-device equivalent of the platform's consent manifest. Records who
consented, to what, when, and the scope — hashed into a tamper-evident
chain. Consent can be withdrawn; withdrawal is also recorded.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from valo_edge.governance.canonical import canonical_digest

_GENESIS = "0" * 64


@dataclass
class ConsentRecord:
    subject: str
    purpose: str
    scope: str
    status: str  # granted | withdrawn
    timestamp_iso: str
    prev_hash: str = _GENESIS
    record_hash: Optional[str] = None

    def _body(self) -> Dict:
        return {
            "subject": self.subject,
            "purpose": self.purpose,
            "scope": self.scope,
            "status": self.status,
            "timestamp_iso": self.timestamp_iso,
            "prev_hash": self.prev_hash,
        }

    def compute_hash(self) -> str:
        return canonical_digest(self._body())


class MicroConsentLedger:
    """Append-only consent ledger with withdrawal support."""

    def __init__(self) -> None:
        self._records: List[ConsentRecord] = []
        self._tail_hash = _GENESIS
        self._current: Dict[str, ConsentRecord] = {}

    def grant(self, subject: str, purpose: str, scope: str, timestamp_iso: str) -> ConsentRecord:
        return self._append(
            ConsentRecord(
                subject=subject, purpose=purpose, scope=scope,
                status="granted", timestamp_iso=timestamp_iso,
            )
        )

    def withdraw(self, subject: str, purpose: str, timestamp_iso: str) -> ConsentRecord:
        record = self._append(
            ConsentRecord(
                subject=subject, purpose=purpose, scope="",
                status="withdrawn", timestamp_iso=timestamp_iso,
            )
        )
        self._current.pop((subject, purpose), None)
        return record

    def _append(self, record: ConsentRecord) -> ConsentRecord:
        record.prev_hash = self._tail_hash
        record.record_hash = record.compute_hash()
        self._records.append(record)
        self._tail_hash = record.record_hash
        if record.status == "granted":
            self._current[(record.subject, record.purpose)] = record
        return record

    def is_active(self, subject: str, purpose: str) -> bool:
        return (subject, purpose) in self._current

    def verify(self) -> bool:
        prev = _GENESIS
        for idx, r in enumerate(self._records):
            if r.prev_hash != prev:
                return False
            if r.compute_hash() != r.record_hash:
                return False
            prev = r.record_hash
        return prev == self._tail_hash

    def read_all(self) -> List[Dict]:
        return [
            {
                "subject": r.subject, "purpose": r.purpose, "scope": r.scope,
                "status": r.status, "timestamp_iso": r.timestamp_iso,
                "record_hash": r.record_hash,
            }
            for r in self._records
        ]
