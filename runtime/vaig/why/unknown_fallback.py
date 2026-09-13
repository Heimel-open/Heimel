"""
UNKNOWN Fallback — Conservative safety semantics.

Rule: UNKNOWN != SAFE
When the system cannot determine a known distrust level, it halts.

This module is standalone. Not wired into ensemble.py or unified_distrust.py.
Wiring is deferred to the consolidation PR.
"""

from dataclasses import dataclass, field
from typing import Dict, Any
import time


# Valid distrust levels
VALID_LEVELS = {0, 1, 2, 3, 4}

# Conservative fallback: UNKNOWN -> HALT
UNKNOWN_FALLBACK = {
    "level": 4,
    "label": "UNKNOWN",
    "action": "HALT",
    "reason": "Unknown distrust level — conservative halt",
}


@dataclass
class FallbackDecision:
    """
    A decision produced by the conservative fallback handler.

    If the input level was valid, this mirrors the input.
    If the input level was unknown, this is the conservative HALT fallback.
    """
    original_level: int
    effective_level: int
    label: str
    action: str
    was_unknown: bool
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


def apply_fallback(level: int, label: str = "", action: str = "") -> FallbackDecision:
    """
    Apply conservative fallback semantics to a distrust level.

    Args:
        level: The distrust level to validate
        label: Optional label from the source system
        action: Optional action from the source system

    Returns:
        FallbackDecision: Either the original decision (if valid) or
                         the conservative HALT fallback (if unknown)

    Rule:
        - Valid levels (0-4): pass through unchanged
        - Invalid levels (anything else): HALT with effective_level=4
    """
    if level in VALID_LEVELS:
        return FallbackDecision(
            original_level=level,
            effective_level=level,
            label=label or _level_to_label(level),
            action=action or _level_to_action(level),
            was_unknown=False,
            reason=f"Valid level {level}",
        )

    # UNKNOWN: conservative fallback to HALT
    return FallbackDecision(
        original_level=level,
        effective_level=UNKNOWN_FALLBACK["level"],
        label=UNKNOWN_FALLBACK["label"],
        action=UNKNOWN_FALLBACK["action"],
        was_unknown=True,
        reason=UNKNOWN_FALLBACK["reason"],
    )


def is_valid_level(level: int) -> bool:
    """Check if a distrust level is valid."""
    return level in VALID_LEVELS


def _level_to_label(level: int) -> str:
    """Convert a valid level to its label."""
    labels = {0: "TRUSTED", 1: "MONITOR", 2: "WARN", 3: "DEGRADE", 4: "HALT"}
    return labels.get(level, "UNKNOWN")


def _level_to_action(level: int) -> str:
    """Convert a valid level to its action."""
    actions = {0: "PASS", 1: "PASS", 2: "WARN", 3: "DEGRADE", 4: "HALT"}
    return actions.get(level, "HALT")
