"""Embedded revocation log — M-of-N guardians, hash-chained, stdlib-only.

On-device equivalent of the platform's ``action_contracts.revocation_log``.
Guardians propose and vote to revoke a key; revocation executes only when the
M-of-N threshold is met. Entries form a hash chain so tampering is detected.
"""

from __future__ import annotations

import hashlib
import json
import time
from typing import Dict, List

from valo_edge.governance.canonical import canonical_digest

_GENESIS = "0" * 64


class RevocationLog:
    """M-of-N guardian revocation with an immutable append-only chain."""

    def __init__(self, threshold: int = 3) -> None:
        self.threshold = threshold
        self._entries: List[Dict] = []
        self._chain_hash = _GENESIS

    def propose_revocation(
        self, target_key: str, reason: str, proposer: str, proposer_sig: str
    ) -> Dict:
        return {
            "type": "REVOCATION_PROPOSAL",
            "target_key": target_key,
            "reason": reason,
            "proposer": proposer,
            "proposer_sig": proposer_sig,
            "timestamp": time.time(),
            "votes": {proposer: proposer_sig},
        }

    def vote(self, proposal: Dict, voter: str, voter_sig: str) -> Dict:
        proposal["votes"][voter] = voter_sig
        return proposal

    def execute(self, proposal: Dict) -> bool:
        if len(proposal.get("votes", {})) < self.threshold:
            return False
        entry = {
            "timestamp": time.time(),
            "target_key": proposal["target_key"],
            "reason": proposal["reason"],
            "votes": list(proposal["votes"].keys()),
            "prev_hash": self._chain_hash,
        }
        entry["hash"] = canonical_digest(
            {k: v for k, v in entry.items() if k != "hash"}
        )
        self._chain_hash = entry["hash"]
        self._entries.append(entry)
        return True

    def is_revoked(self, key: str) -> bool:
        return any(e["target_key"] == key for e in self._entries)

    def verify(self) -> bool:
        prev = _GENESIS
        for e in self._entries:
            if e["prev_hash"] != prev:
                return False
            test = {k: v for k, v in e.items() if k != "hash"}
            if e["hash"] != canonical_digest(test):
                return False
            prev = e["hash"]
        return prev == self._chain_hash
