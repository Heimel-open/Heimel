"""
CAN / SHOULD / WHY governance signal model.

Three axes:
  CAN    — capability / tool permission
  SHOULD — policy / admissibility
  WHY    — justification continuity

Supporting:
  WORM   — proof / evidence chain integrity
  SSIP   — governance state self-integrity

Aggregation: weakest link = worst(CAN, SHOULD, WHY).
PURPLE override: if WORM or SSIP degraded, overall is PURPLE regardless.

Spec: docs/can-should-why-vu-meter.md
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class SignalLevel(IntEnum):
    GREEN = 0
    YELLOW = 1
    ORANGE = 2
    RED = 3
    PURPLE = 4

    @property
    def label(self) -> str:
        _labels = {
            SignalLevel.GREEN: "GREEN",
            SignalLevel.YELLOW: "YELLOW",
            SignalLevel.ORANGE: "ORANGE",
            SignalLevel.RED: "RED",
            SignalLevel.PURPLE: "PURPLE",
        }
        return _labels[self]

    @property
    def action(self) -> str:
        _actions = {
            SignalLevel.GREEN: "Continue",
            SignalLevel.YELLOW: "Watch",
            SignalLevel.ORANGE: "Human review required",
            SignalLevel.RED: "Halt — consequence blocked",
            SignalLevel.PURPLE: "Forensic mode — governance state in question",
        }
        return _actions[self]

    @property
    def is_consequence_blocked(self) -> bool:
        return self in (SignalLevel.RED, SignalLevel.PURPLE)


@dataclass
class OverlaySignals:
    can: SignalLevel = SignalLevel.GREEN
    should: SignalLevel = SignalLevel.GREEN
    why: SignalLevel = SignalLevel.GREEN
    worm_ok: bool = True
    ssip_ok: bool = True
    reason: str = ""


def aggregate(signals: OverlaySignals) -> SignalLevel:
    """
    Weakest-link aggregation.

    PURPLE override: if WORM or SSIP integrity is degraded, the overall
    status is PURPLE regardless of CAN / SHOULD / WHY values.
    Consequence commitment is disabled under PURPLE.
    """
    if not signals.worm_ok or not signals.ssip_ok:
        return SignalLevel.PURPLE

    return max(signals.can, signals.should, signals.why)
