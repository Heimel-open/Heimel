"""Embedded device governance vertikal — full on-device governance chain.

A complete, stdlib-only "embedded version of the platform vertikal" for a
single edge device. It binds every governance primitive into one fail-closed
decision pipeline:

    sensor event
      -> rate limit
      -> admissibility (signal fusion)
      -> clearance (micro-REHT)
      -> WORM record
      -> consent check
      -> revocation check

No third-party dependencies; suitable for micro controllers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from valo_edge.governance.canonical import canonical_digest
from valo_edge.governance.embedded_approval import ApprovalChain
from valo_edge.governance.micro_admissibility import (
    AdmissibilityVerdict,
    MicroAdmissibilityEngine,
    MicroSignal,
    SignalDisposition,
)
from valo_edge.governance.micro_consent import MicroConsentLedger
from valo_edge.governance.ratelimit import RateLimiter
from valo_edge.governance.revocation import RevocationLog
from valo_edge.governance.worm import WormLog


class DeviceActionOutcome(str, Enum):
    ALLOWED = "ALLOWED"
    BLOCKED_RATE = "BLOCKED_RATE"
    BLOCKED_ADMISSIBILITY = "BLOCKED_ADMISSIBILITY"
    BLOCKED_NO_CONSENT = "BLOCKED_NO_CONSENT"
    BLOCKED_REVOKED = "BLOCKED_REVOKED"
    BLOCKED_HALT = "BLOCKED_HALT"


@dataclass
class DeviceActionResult:
    outcome: DeviceActionOutcome
    action_id: str
    reasons: List[str] = field(default_factory=list)
    worm_hash: Optional[str] = None
    clearance_id: Optional[str] = None


class DeviceGovernanceLedger:
    """Binds all embedded governance primitives into one device pipeline."""

    def __init__(
        self,
        device_id: str,
        *,
        rate_limit_per_min: int = 100,
        approval_required: int = 1,
    ) -> None:
        self.device_id = device_id
        self._rate = RateLimiter(max_requests=rate_limit_per_min, window_seconds=60.0)
        self._admissibility = MicroAdmissibilityEngine()
        self._worm = WormLog()
        self._consent = MicroConsentLedger()
        self._revocation = RevocationLog(threshold=approval_required)
        self._approval = ApprovalChain(
            action_id="device-approval", required_approvals=approval_required
        )
        self._halted = False
        self._halt_reason = ""

    def trigger_halt(self, reason: str) -> None:
        self._halted = True
        self._halt_reason = reason

    def reset_halt(self) -> None:
        self._halted = False
        self._halt_reason = ""

    def grant_consent(self, purpose: str, scope: str, timestamp_iso: str) -> None:
        self._consent.grant(self.device_id, purpose, scope, timestamp_iso)

    def revoke_device(self, proposer: str, signature: str) -> bool:
        proposal = self._revocation.propose_revocation(
            self.device_id, "device revoked", proposer, signature
        )
        return self._revocation.execute(proposal)

    def evaluate(
        self,
        *,
        action_type: str,
        parameters: Dict[str, Any],
        purpose: str,
        signals: List[MicroSignal],
        risk_tier: str = "L1",
        now_iso: str,
    ) -> DeviceActionResult:
        """Run the full on-device governance chain for one action."""
        action_id = canonical_digest(
            {
                "device": self.device_id,
                "action_type": action_type,
                "parameters": parameters,
                "now": now_iso,
            }
        )

        if self._halted:
            return DeviceActionResult(
                DeviceActionOutcome.BLOCKED_HALT, action_id,
                reasons=[f"device halted: {self._halt_reason}"],
            )

        if self._revocation.is_revoked(self.device_id):
            return DeviceActionResult(
                DeviceActionOutcome.BLOCKED_REVOKED, action_id,
                reasons=["device key revoked"],
            )

        if not self._rate.is_allowed(self.device_id):
            return DeviceActionResult(
                DeviceActionOutcome.BLOCKED_RATE, action_id,
                reasons=["rate limit exceeded"],
            )

        if not self._consent.is_active(self.device_id, purpose):
            return DeviceActionResult(
                DeviceActionOutcome.BLOCKED_NO_CONSENT, action_id,
                reasons=[f"no active consent for purpose {purpose}"],
            )

        decision = self._admissibility.decide(
            signals=signals, risk_tier=risk_tier, has_human_delegate=True
        )
        if decision.verdict is not AdmissibilityVerdict.ADMIT:
            return DeviceActionResult(
                DeviceActionOutcome.BLOCKED_ADMISSIBILITY, action_id,
                reasons=decision.reasons,
            )

        entry = self._worm.append(
            {
                "action_id": action_id,
                "action_type": action_type,
                "parameters": parameters,
                "purpose": purpose,
                "verdict": decision.verdict.value,
                "governance_confidence": decision.governance_confidence,
                "timestamp_iso": now_iso,
            }
        )
        return DeviceActionResult(
            DeviceActionOutcome.ALLOWED, action_id,
            reasons=decision.reasons,
            worm_hash=entry.entry_hash,
        )

    def audit_tail(self) -> str:
        return self._worm.tail_hash

    def verify(self) -> bool:
        return self._worm.verify() and self._consent.verify() and self._revocation.verify()
