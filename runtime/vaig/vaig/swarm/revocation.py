"""
VAIG Swarm — WORM Revocation Log
M-of-N guardians required to revoke a key. Immutable append-only.
"""
import time
import hashlib
import json

class RevocationLog:
    """
    M-of-N revocation: M guardians must sign to revoke a key.
    Entries are WORM (Write Once Read Many) — append-only.
    """

    def __init__(self, threshold: int = 3):
        self.threshold = threshold
        self._entries = []
        self._chain_hash = "0" * 64

    def propose_revocation(self, target_key: str, reason: str,
                           proposer: str, proposer_sig: str) -> dict:
        """Propose revoking a key. Returns proposal for other guardians to sign."""
        proposal = {
            "type": "REVOCATION_PROPOSAL",
            "target_key": target_key,
            "reason": reason,
            "proposer": proposer,
            "proposer_sig": proposer_sig,
            "timestamp": time.time(),
            "votes": {proposer: proposer_sig},
        }
        return proposal

    def vote(self, proposal: dict, voter: str, voter_sig: str) -> dict:
        """Add a vote to a revocation proposal."""
        proposal["votes"][voter] = voter_sig
        return proposal

    def execute(self, proposal: dict) -> bool:
        """Execute revocation if threshold met."""
        if len(proposal["votes"]) < self.threshold:
            return False

        entry = {
            "timestamp": time.time(),
            "target_key": proposal["target_key"],
            "reason": proposal["reason"],
            "votes": list(proposal["votes"].keys()),
            "prev_hash": self._chain_hash,
        }
        entry["hash"] = hashlib.sha256(json.dumps(entry, sort_keys=True).encode()).hexdigest()
        self._chain_hash = entry["hash"]
        self._entries.append(entry)
        return True

    def is_revoked(self, key: str) -> bool:
        """Check if a key has been revoked."""
        return any(e["target_key"] == key for e in self._entries)

    def verify(self) -> bool:
        """Verify WORM integrity."""
        prev = "0" * 64
        for e in self._entries:
            if e["prev_hash"] != prev:
                return False
            test = {k: v for k, v in e.items() if k != "hash"}
            expected = hashlib.sha256(json.dumps(test, sort_keys=True).encode()).hexdigest()
            if e["hash"] != expected:
                return False
            prev = e["hash"]
        return True
