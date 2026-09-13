"""Operational deferment modes for SSIP."""

from __future__ import annotations

from enum import Enum


class DefermentMode(str, Enum):
    """Operational mode selected during governance degradation."""

    NORMAL = "NORMAL"
    MONITORING = "MONITORING"
    RESTRICTED = "RESTRICTED"
    ISOLATION = "ISOLATION"


def deferment_for_signal(hsrs_level: str, oob_consistent: bool = True) -> DefermentMode:
    """Map high-level governance signals to SSIP deferment mode.

    This is intentionally minimal v0.1 logic. Full hysteresis and duration
    windows belong in a later policy module.
    """

    level = hsrs_level.upper().strip()
    if not oob_consistent:
        return DefermentMode.ISOLATION
    if level == "CRITICAL":
        return DefermentMode.ISOLATION
    if level == "HIGH":
        return DefermentMode.RESTRICTED
    if level == "MEDIUM":
        return DefermentMode.MONITORING
    return DefermentMode.NORMAL
