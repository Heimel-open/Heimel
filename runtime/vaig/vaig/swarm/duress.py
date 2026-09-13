"""
VAIG Swarm — Duress Code System
Silent alert: correct code → normal. Duress code → grants access BUT silently 
alerts authority that operator is under coercion.
"""
import hashlib
import hmac
import os
import time
from typing import Optional

class DuressAuth:
    """
    Two-code system:
      - Normal code: full access, no alert
      - Duress code: grants access + silent alert to swarm

    Codes are stored as salted HMAC-SHA256 digests with a per-instance
    random salt, so a leaked digest table is not directly brute-forceable.
    """

    _DIGEST_BYTES = 32

    def __init__(self):
        self._normal_digest: Optional[bytes] = None
        self._duress_digest: Optional[bytes] = None
        self._salt: Optional[bytes] = None
        self._alert_log = []

    def set_codes(self, normal_code: str, duress_code: str):
        """Set both codes (run once at initialization)."""
        self._salt = os.urandom(self._DIGEST_BYTES)
        self._normal_digest = self._digest(normal_code)
        self._duress_digest = self._digest(duress_code)

    def authenticate(self, code: str) -> tuple[bool, bool]:
        """
        Returns: (access_granted, is_duress)
        If duress: access is granted BUT alert is silently logged.
        """
        d = self._digest(code)
        if d == self._normal_digest:
            return True, False
        if d == self._duress_digest:
            self._alert_log.append({
                "timestamp": time.time(),
                "type": "DURESS_ALERT",
                "message": "Operator under coercion — access granted as cover"
            })
            return True, True
        return False, False

    def get_alerts(self) -> list:
        """Retrieve duress alerts (for authority review)."""
        return self._alert_log.copy()

    def _digest(self, code: str) -> bytes:
        if self._salt is None:
            raise RuntimeError("set_codes() must be called before authenticate()")
        return hmac.new(self._salt, code.encode(), hashlib.sha256).digest()
