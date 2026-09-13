"""
VAIG Swarm — Orchestrator
Full anti-coercion / kidnapping resistance system.
Combines: duress, time-lock, Shamir, VRF, ring signatures, epoch rotation, revocation.
"""
from typing import List, Optional, Dict
import time

from .duress import DuressAuth
from .time_lock import TimeLock
from .shamir import ShamirSecretSharing
from .vrf import VRF
from .ring_sig import RingSignature
from .epoch import EpochManager
from .revocation import RevocationLog

class SwarmOrchestrator:
    """
    Complete swarm authority for VALO-protected AI systems.

    Features:
      - Duress codes: Silent alert under coercion
      - Time-locked auth: 15-min delay for critical ops
      - Shamir secret sharing: (100, 3) threshold
      - VRF: Verifiable random active set rotation
      - Ring signatures: Anonymous guardian voting
      - Epoch rotation: Hourly key refresh
      - Revocation: M-of-N guardian key revocation (WORM)

    Usage:
        swarm = SwarmOrchestrator(n_guardians=100, threshold=3)
        swarm.bootstrap(guardian_ids)

        # Normal authentication
        ok, is_duress = swarm.authenticate("normal_code")

        # Time-locked critical operation
        unlock_time = swarm.request_critical_op("disable_l1", "guardian_1")
        # ... 15 minutes later ...
        ok, msg = swarm.confirm_critical_op("disable_l1")
    """

    def __init__(self, n_guardians: int = 100, threshold: int = 3):
        self.n = n_guardians
        self.k = threshold

        self.duress = DuressAuth()
        self.timelock = TimeLock()
        self.shamir = ShamirSecretSharing(n=n_guardians, k=threshold)
        self.vrf = VRF()
        self.ring = RingSignature(ring_size=n_guardians)
        self.epoch = EpochManager()
        self.revocation = RevocationLog(threshold=threshold)

        self._guardians: List[str] = []
        self._master_secret: Optional[int] = None
        self._shares: List = []

    def bootstrap(self, guardian_ids: List[str], master_secret: int,
                  normal_code: str, duress_code: str):
        """Initialize the swarm with guardians and secrets."""
        self._guardians = guardian_ids[:self.n]
        self._master_secret = master_secret

        # Set duress codes
        self.duress.set_codes(normal_code, duress_code)

        # Split master secret via Shamir
        self._shares = self.shamir.split(master_secret)

        # Rotate to initial epoch
        self.epoch.rotate_keys(self._guardians)

        return {
            "guardians": len(self._guardians),
            "shares_distributed": len(self._shares),
            "epoch": self.epoch.current_epoch(),
        }

    def authenticate(self, code: str) -> tuple[bool, bool]:
        """Authenticate via duress system. Returns (access, is_duress)."""
        return self.duress.authenticate(code)

    def request_critical_op(self, op_id: str, requester: str) -> float:
        """Request a time-locked critical operation. Returns unlock timestamp."""
        full_id = f"{op_id}:{requester}:{self.epoch.current_epoch()}"
        return self.timelock.request(full_id)

    def confirm_critical_op(self, op_id: str, requester: str) -> tuple[bool, str]:
        """Confirm critical op after time lock."""
        full_id = f"{op_id}:{requester}:{self.epoch.current_epoch()}"
        return self.timelock.confirm(full_id)

    def propose_revocation(self, target_key: str, reason: str,
                           proposer: str, proposer_sig: str) -> dict:
        """Propose revoking a compromised key."""
        return self.revocation.propose_revocation(target_key, reason, proposer, proposer_sig)

    def vote_revocation(self, proposal: dict, voter: str, voter_sig: str) -> dict:
        """Vote on a revocation proposal."""
        return self.revocation.vote(proposal, voter, voter_sig)

    def execute_revocation(self, proposal: dict) -> bool:
        """Execute revocation if threshold met."""
        return self.revocation.execute(proposal)

    def status(self) -> dict:
        """Full swarm status."""
        return {
            "guardians": len(self._guardians),
            "threshold": self.k,
            "epoch": self.epoch.current_epoch(),
            "duress_alerts": len(self.duress.get_alerts()),
            "revocations": len(self.revocation._entries),
            "pending_ops": len(self.timelock._pending),
        }
