"""Embedded device governance — full on-device governance vertikal.

The "embedded version of a platform vertikal": one component that binds all
governance primitives into a single fail-closed pipeline for a device.
"""

from valo_edge.device.ledger import (
    DeviceActionResult,
    DeviceActionOutcome,
    DeviceGovernanceLedger,
)

__all__ = [
    "DeviceActionResult",
    "DeviceActionOutcome",
    "DeviceGovernanceLedger",
]
