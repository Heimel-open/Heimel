"""
OverlayStatus — computed governance status object for operator display.

Drives the compact / expanded / purple display formats defined in
docs/can-should-why-vu-meter.md.

Do not embed private thresholds in this module — expose receipt hash
references only. Display constants live in UI layers, not here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from vaig.management_overlay.signals.can_should_why import (
    OverlaySignals,
    SignalLevel,
    aggregate,
)


@dataclass
class OverlayStatus:
    signals: OverlaySignals
    overall: SignalLevel
    receipt_hash: Optional[str] = None

    @classmethod
    def compute(
        cls,
        signals: OverlaySignals,
        receipt_hash: Optional[str] = None,
    ) -> "OverlayStatus":
        overall = aggregate(signals)
        return cls(signals=signals, overall=overall, receipt_hash=receipt_hash)

    @property
    def consequence_commitment_enabled(self) -> bool:
        return not self.overall.is_consequence_blocked

    @property
    def requires_human_review(self) -> bool:
        return self.overall >= SignalLevel.ORANGE


def _bar(level: SignalLevel, width: int = 8) -> str:
    filled = max(1, width - int(level) * 2)
    return "=" * filled + " " * (width - filled)


def render_compact(status: OverlayStatus) -> str:
    overall = status.overall
    lines = [
        f"VALO: {overall.label} — {overall.action.upper().split('—')[0].strip()}",
        f"Reason: {status.signals.reason or overall.action}",
    ]
    if status.receipt_hash:
        lines.append(f"Receipt: WORM hash {status.receipt_hash[:16]}...")
    else:
        lines.append("Receipt: WORM hash available" if status.signals.worm_ok else "Receipt: WORM INTEGRITY DEGRADED")
    return "\n".join(lines)


def render_expanded(status: OverlayStatus) -> str:
    s = status.signals
    overall = status.overall

    if overall == SignalLevel.PURPLE:
        receipt_line = "Evidence: PRESERVED"
        return "\n".join([
            "STATUS: PURPLE — SYSTEM TRUST EVENT",
            f"Reason: {s.reason or 'OOB / WORM / SSIP integrity degraded'}",
            "Consequence commitment: DISABLED",
            receipt_line,
        ])

    w = 8
    lines = [
        f"CAN     [{_bar(s.can, w)}] {s.can.label}",
        f"SHOULD  [{_bar(s.should, w)}] {s.should.label}",
        f"WHY     [{_bar(s.why, w)}] {s.why.label}",
        "",
        f"STATUS: {overall.label} — {overall.action.upper()}",
        f"Reason: {s.reason or overall.action}",
    ]
    if status.receipt_hash:
        lines.append(f"Receipt: WORM hash {status.receipt_hash[:16]}...")
    else:
        lines.append("Receipt: WORM hash available")
    return "\n".join(lines)
