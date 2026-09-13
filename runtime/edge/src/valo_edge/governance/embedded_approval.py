"""Embedded approval chain — quorum-gated, hash-chained, stdlib-only.

On-device equivalent of the platform's approval chain / quorum logic.
An action requiring approval collects approver votes; it is approved only
when the required quorum is met. Each approval record is appended to a
hash chain so the audit trail is tamper-evident.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from valo_edge.governance.canonical import canonical_digest

_GENESIS = "0" * 64


@dataclass
class ApprovalRecord:
    action_id: str
    approver: str
    decision: str  # approve | reject | abstain
    reason: str = ""
    prev_hash: str = _GENESIS
    record_hash: Optional[str] = None

    def _body(self) -> Dict:
        return {
            "action_id": self.action_id,
            "approver": self.approver,
            "decision": self.decision,
            "reason": self.reason,
            "prev_hash": self.prev_hash,
        }

    def compute_hash(self) -> str:
        return canonical_digest(self._body())


class ApprovalChain:
    """Quorum-gated approval with an immutable, tamper-evident chain."""

    def __init__(self, action_id: str, required_approvals: int = 1) -> None:
        if required_approvals < 1:
            raise ValueError("required_approvals must be >= 1")
        self.action_id = action_id
        self.required_approvals = required_approvals
        self._records: List[ApprovalRecord] = []
        self._tail_hash = _GENESIS

    def add_vote(self, approver: str, decision: str, reason: str = "") -> ApprovalRecord:
        if decision not in ("approve", "reject", "abstain"):
            raise ValueError(f"invalid decision: {decision}")
        record = ApprovalRecord(
            action_id=self.action_id,
            approver=approver,
            decision=decision,
            reason=reason,
            prev_hash=self._tail_hash,
        )
        record.record_hash = record.compute_hash()
        self._records.append(record)
        self._tail_hash = record.record_hash
        return record

    @property
    def approval_count(self) -> int:
        return sum(1 for r in self._records if r.decision == "approve")

    @property
    def is_approved(self) -> bool:
        return self.approval_count >= self.required_approvals

    def verify(self) -> bool:
        prev = _GENESIS
        for idx, r in enumerate(self._records):
            if r.prev_hash != prev:
                return False
            if r.compute_hash() != r.record_hash:
                return False
            prev = r.record_hash
        return prev == self._tail_hash

    def status(self) -> Dict:
        return {
            "action_id": self.action_id,
            "required_approvals": self.required_approvals,
            "approval_count": self.approval_count,
            "is_approved": self.is_approved,
            "chain_verified": self.verify(),
            "tail_hash": self._tail_hash,
        }
