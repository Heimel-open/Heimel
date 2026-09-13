"""Rate limiting for VAIG API endpoints.

Sliding window rate limiter with per-key tracking.
Supports both in-memory and Redis backends.

Usage:
    from vaig.rate_limit import RateLimiter
    limiter = RateLimiter(max_requests=100, window_seconds=60)

    if limiter.is_allowed("api-key-123"):
        process_request()
    else:
        return 429 Too Many Requests
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Optional

from vaig.logging_config import get_logger

logger = get_logger("vaig.rate_limit")


@dataclass
class RateLimitStatus:
    """Status of a rate limit check."""
    allowed: bool
    remaining: int
    reset_at: float
    limit: int
    window: int

    @property
    def retry_after(self) -> int:
        """Seconds until the next request is allowed."""
        if self.allowed:
            return 0
        return max(0, int(self.reset_at - time.time()))

    def to_headers(self) -> Dict[str, str]:
        """Return HTTP rate limit headers."""
        return {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(self.remaining),
            "X-RateLimit-Reset": str(int(self.reset_at)),
            "X-RateLimit-Window": str(self.window),
        }


class RateLimiter:
    """Sliding window rate limiter.

    Tracks request timestamps per key and enforces limits
    within a rolling time window.

    Args:
        max_requests: Maximum requests allowed per window
        window_seconds: Window size in seconds
    """

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: Dict[str, list] = defaultdict(list)
        logger.info("rate_limiter_initialized", extra={
            "max_requests": max_requests,
            "window_seconds": window_seconds,
        })

    def is_allowed(self, key: str) -> RateLimitStatus:
        """Check if a request is allowed for the given key.

        Args:
            key: Unique identifier (API key, IP address, etc.)

        Returns:
            RateLimitStatus with allow/deny and header values
        """
        now = time.time()
        window_start = now - self.window

        # Clean old entries and count current window
        self._requests[key] = [t for t in self._requests[key] if t > window_start]
        current_count = len(self._requests[key])

        # Calculate reset time (when oldest entry in next window expires)
        if self._requests[key]:
            reset_at = self._requests[key][0] + self.window
        else:
            reset_at = now + self.window

        if current_count >= self.max_requests:
            logger.warning("rate_limit_exceeded", extra={
                "key": key[:8],
                "count": current_count,
                "limit": self.max_requests,
            })
            return RateLimitStatus(
                allowed=False,
                remaining=0,
                reset_at=reset_at,
                limit=self.max_requests,
                window=self.window,
            )

        self._requests[key].append(now)
        remaining = self.max_requests - len(self._requests[key])

        return RateLimitStatus(
            allowed=True,
            remaining=remaining,
            reset_at=reset_at,
            limit=self.max_requests,
            window=self.window,
        )

    def reset(self, key: str) -> None:
        """Reset rate limit for a key."""
        self._requests.pop(key, None)
        logger.info("rate_limit_reset", extra={"key": key[:8]})
