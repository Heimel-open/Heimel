from enum import Enum
from typing import Literal


class DistrustLevel(Enum):
    TRUSTED = "L0"
    MONITOR = "L1"
    WARN    = "L2"
    DEGRADE = "L3"
    HALT    = "L4"


GateStatus = Literal["PASS", "DEGRADE", "HALT"]


def level_to_gate_status(level: DistrustLevel) -> GateStatus:
    if level == DistrustLevel.HALT:
        return "HALT"
    if level in (DistrustLevel.WARN, DistrustLevel.DEGRADE):
        return "DEGRADE"
    return "PASS"
