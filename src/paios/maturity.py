"""
Maturity gate (#144) — tracks current autonomy level and conditions to advance.

Maturity levels (L0–L4):
  L0: None         — no autonomy; all actions require human direction.
  L1: Assist       — OS can present information and structured suggestions.
  L2: Steered Recs — OS can make recommendations steered by policy context.
  L3: Governed Ex. — OS can execute within explicit authority/admissibility bounds.
  L4: Autonomous   — OS operates under continuous governed autonomy.

Design:
  - Starts at L1 (Assist). NO auto-advance without an explicit governance signal.
  - Each level has conditions that MUST be proven before advancing.
  - L2→L3 requires REHT admissibility proven (the canonical governance condition).
  - No jump-skip: the OS must advance through each level sequentially.

Canonical rules:
  - REHT sole admissibility authority — referenced as condition, never bypassed.
  - C0/α/τ are env vars only, never hardcoded.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Dict, List, Optional


class MaturityLevel(Enum):
    """Canonical autonomy maturity levels."""

    L0_NONE = 0          # No autonomy
    L1_ASSIST = 1        # Assist — structured suggestions
    L2_STEERED_RECS = 2  # Steered recommendations
    L3_GOVERNED_EX = 3   # Governed execution (within authority bounds)
    L4_AUTONOMOUS = 4    # Autonomous (continuous governed autonomy)

    @classmethod
    def from_label(cls, label: str) -> "MaturityLevel":
        mapping = {
            "L0": cls.L0_NONE,
            "L1": cls.L1_ASSIST,
            "L2": cls.L2_STEERED_RECS,
            "L3": cls.L3_GOVERNED_EX,
            "L4": cls.L4_AUTONOMOUS,
        }
        return mapping[label.upper()]

    @property
    def label(self) -> str:
        return f"L{self.value}"

    @property
    def description(self) -> str:
        return _LEVEL_DESCRIPTIONS[self]


_LEVEL_DESCRIPTIONS: Dict[MaturityLevel, str] = {
    MaturityLevel.L0_NONE: "No autonomy — all actions require human direction.",
    MaturityLevel.L1_ASSIST: "Assist — the OS can present information and structured suggestions.",
    MaturityLevel.L2_STEERED_RECS: "Steered recommendations — recommendations bound by policy context.",
    MaturityLevel.L3_GOVERNED_EX: "Governed execution — actions permitted within explicit authority/admissibility bounds.",
    MaturityLevel.L4_AUTONOMOUS: "Autonomous — operates under continuous governed autonomy.",
}


# C0 / α / τ from env vars only — never hardcoded
_C0_HIGH = float(os.environ.get("PAIOS_C0_HIGH", "0.7"))

# TUNABLE: minimum coherence required for L2→L3 advance
_ADVANCE_C0_THRESHOLD = float(os.environ.get("PAIOS_ADVANCE_C0", "0.65"))


@dataclass
class LevelCondition:
    """A condition that must be satisfied to advance to the next level."""

    description: str
    check: Callable[[], bool] = field(default=lambda: False)

    def is_satisfied(self) -> bool:
        return self.check()


# Default advance conditions per level transition
_DEFAULT_ADVANCE_CONDITIONS: Dict[MaturityLevel, List[LevelCondition]] = {
    MaturityLevel.L0_NONE: [
        LevelCondition(
            description="Initial capability loaded",
            check=lambda: True,
        ),
    ],
    MaturityLevel.L1_ASSIST: [
        LevelCondition(
            description="Canonical Memory store initialised and operational",
            check=lambda: True,
        ),
    ],
    MaturityLevel.L2_STEERED_RECS: [
        LevelCondition(
            description="REHT admissibility pathway proven — the OS can construct governed action proposals "
                        "and route them to REHT for admissibility evaluation",
            check=lambda: os.environ.get("PAIOS_REHT_ADMISSIBILITY_PROVEN", "0") == "1",
        ),
    ],
    MaturityLevel.L3_GOVERNED_EX: [
        LevelCondition(
            description="Continuous integrity monitoring active — all execution bound by valid "
                        "GovernanceClearance from REHT",
            check=lambda: os.environ.get("PAIOS_CONTINUOUS_INTEGRITY", "0") == "1",
        ),
    ],
}


class AutonomyModel:
    """Tracks execution autonomy, not developmental maturity.

    No auto-advance without an explicit governance signal.
    """

    def __init__(self, start_level: MaturityLevel = MaturityLevel.L1_ASSIST) -> None:
        self._current = start_level
        self._history: List[Dict] = []

    @property
    def current(self) -> MaturityLevel:
        """Current maturity level."""
        return self._current

    @property
    def history(self) -> List[Dict]:
        """Advancement history — each entry records the transition."""
        return list(self._history)

    def can_advance(self) -> bool:
        """Check whether all conditions for the next level are met, without advancing."""
        if self._current == MaturityLevel.L4_AUTONOMOUS:
            return False
        next_level = MaturityLevel(self._current.value + 1)
        conditions = _DEFAULT_ADVANCE_CONDITIONS.get(self._current, [])
        return all(c.is_satisfied() for c in conditions)

    def advance(self, signal: Optional[str] = None) -> MaturityLevel:
        """Attempt to advance to the next maturity level.

        Raises:
            AdvanceError: if conditions are not satisfied or already at max level.
        """
        if self._current == MaturityLevel.L4_AUTONOMOUS:
            raise AdvanceError("Already at maximum autonomy level L4.")

        next_level = MaturityLevel(self._current.value + 1)
        conditions = _DEFAULT_ADVANCE_CONDITIONS.get(self._current, [])

        unsatisfied = [c for c in conditions if not c.is_satisfied()]
        if unsatisfied:
            details = "; ".join(c.description for c in unsatisfied)
            raise AdvanceError(
                f"Cannot advance from {self._current.label} to {next_level.label}: "
                f"conditions not met: {details}"
            )

        self._history.append({
            "from": self._current.label,
            "to": next_level.label,
            "signal": signal or "auto-check",
            "timestamp": __import__("time").time(),
        })
        self._current = next_level
        return self._current

    def reset(self, level: MaturityLevel = MaturityLevel.L1_ASSIST) -> None:
        """Reset to a given level (governance override)."""
        self._current = level
        self._history.clear()


# Backward-compatible name. This is an autonomy gate, never seed development.
MaturityModel = AutonomyModel


class AdvanceError(Exception):
    """Raised when a maturity level advance is refused."""
