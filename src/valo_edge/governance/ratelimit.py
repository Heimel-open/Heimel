"""Embedded sliding-window rate limiter — stdlib-only.

On-device equivalent of the platform's sliding-window limiter. Enforces a
max requests per rolling window per key with no external dependencies.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque, Dict


class RateLimiter:
    """Sliding-window rate limiter keyed by identifier."""

    def __init__(self, max_requests: int = 100, window_seconds: float = 60.0) -> None:
        if max_requests <= 0:
            raise ValueError("max_requests must be positive")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str, now: float | None = None) -> bool:
        """Return True if a request for ``key`` is allowed now."""
        now = time.time() if now is None else now
        cutoff = now - self.window
        dq = self._requests[key]
        while dq and dq[0] <= cutoff:
            dq.popleft()
        if len(dq) >= self.max_requests:
            return False
        dq.append(now)
        return True

    def remaining(self, key: str, now: float | None = None) -> int:
        now = time.time() if now is None else now
        cutoff = now - self.window
        dq = self._requests[key]
        while dq and dq[0] <= cutoff:
            dq.popleft()
        return max(0, self.max_requests - len(dq))

    def reset(self, key: str) -> None:
        self._requests.pop(key, None)
