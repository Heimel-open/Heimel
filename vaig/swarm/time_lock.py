"""
VAIG Swarm — Time-Locked Authentication
15-minute delay for critical operations. Prevents impulse/forced decisions.
"""
import time
from typing import Optional

class TimeLock:
    """
    Two-phase commit for critical operations:
      1. Request: locks operation, starts 15-min timer
      2. Confirm (after 15 min): executes if not cancelled
    """

    DELAY_SECONDS = 15 * 60  # 15 minutes

    def __init__(self):
        self._pending = {}  # op_id -> request_time

    def request(self, operation_id: str) -> float:
        """Request a time-locked operation. Returns unlock timestamp."""
        unlock_at = time.time() + self.DELAY_SECONDS
        self._pending[operation_id] = unlock_at
        return unlock_at

    def confirm(self, operation_id: str) -> tuple[bool, str]:
        """
        Confirm operation after delay.
        Returns: (success, message)
        """
        if operation_id not in self._pending:
            return False, "Operation not found or expired"

        unlock_at = self._pending[operation_id]
        remaining = unlock_at - time.time()

        if remaining > 0:
            return False, f"Wait {remaining:.0f}s more"

        del self._pending[operation_id]
        return True, "Operation approved after time lock"

    def cancel(self, operation_id: str) -> bool:
        """Cancel a pending operation."""
        if operation_id in self._pending:
            del self._pending[operation_id]
            return True
        return False

    def status(self, operation_id: str) -> Optional[float]:
        """Get remaining seconds, or None if not pending."""
        if operation_id not in self._pending:
            return None
        return max(0, self._pending[operation_id] - time.time())
