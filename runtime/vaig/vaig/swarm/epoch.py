"""
VAIG Swarm — Epoch-Based Key Rotation
Keys refreshed every epoch. Old keys cannot sign new epochs (prevents replay).

NOTE: conceptual implementation — keys are random 32-byte CSPRNG values,
but this is not an audited KDF. Review before production use.
"""
import secrets
import time
import hashlib

class EpochManager:
    """
    Divides time into epochs (e.g., 1 hour).
    Keys are epoch-bound: epoch N keys cannot sign epoch N+1.
    """

    EPOCH_DURATION = 3600  # 1 hour in seconds
    _KEY_BYTES = 32

    def __init__(self):
        self._keys = {}  # epoch -> {guardian: hex_key}
        self._current_epoch = self._get_epoch()

    def _get_epoch(self) -> int:
        return int(time.time() // self.EPOCH_DURATION)

    def current_epoch(self) -> int:
        return self._get_epoch()

    def rotate_keys(self, guardians: list):
        """Generate new epoch keys for all guardians."""
        epoch = self.current_epoch()
        self._keys[epoch] = {}
        for g in guardians:
            self._keys[epoch][g] = secrets.token_hex(self._KEY_BYTES)
        self._current_epoch = epoch
        return epoch

    def get_key(self, guardian: str, epoch: int = None) -> str:
        """Get key for guardian in specific epoch."""
        epoch = epoch or self.current_epoch()
        return self._keys.get(epoch, {}).get(guardian)

    def is_valid_epoch(self, epoch: int) -> bool:
        """Check if epoch is current or recent (not too old)."""
        current = self.current_epoch()
        return current - 2 <= epoch <= current
