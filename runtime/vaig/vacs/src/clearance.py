"""Canonical REHT GovernanceClearance for the VACS execution boundary.

VAIG EVALUATES; REHT CLEARS. A VAIG-local policy result (Decision) is an
evaluation/recommendation only — it is NOT execution authority. The execution
handoff boundary (execution_adapter.ExecutionHandoffAdapter) MUST require a
verified REHT ``GovernanceClearance`` before it may return status=READY.

This module defines the clearance structure and the verification routine that
binds the clearance to the packet it authorizes (purpose record/version,
authority, execution state, policy, evidence fingerprint, evaluator). It is a
structural reference implementation: signature verification is delegated to the
REHT verification layer and is represented here by an ``is_verified`` flag plus
a ``signature`` field, so a forged/unsigned clearance fails closed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ClearanceStatus(Enum):
    VALID = "valid"
    MISSING = "missing"
    EXPIRED = "expired"
    STALE = "stale"
    MISMATCHED = "mismatched"
    SUPERSEDED = "superseded"
    UNVERIFIED = "unverified"


# Bounds for "fresh enough" clearance. A clearance issued older than this is
# treated as STALE and cannot authorize execution.
MAX_CLEARANCE_AGE_SECONDS = 300


@dataclass
class GovernanceClearance:
    """Canonical REHT governance clearance.

    Binds the authorized execution to its full governance context so a clearance
    cannot be replayed against a different packet, purpose, provider, state or
    evidence set.
    """

    clearance_id: str
    # Packet this clearance authorizes (anti-replay binding).
    packet_id: str
    # Purpose record binding.
    purpose_record: str
    purpose_version: str
    # Authority / evaluator that issued the clearance.
    authority: str
    evaluator: str
    # Execution state / policy the clearance is scoped to.
    execution_state: str
    policy_id: str
    # Evidence fingerprint the clearance covers.
    evidence_fingerprint: str
    # Time bounds.
    issued_at: str
    expires_at: str
    # Signature by the REHT clearance authority. Empty/placeholder => unverified.
    signature: str = ""
    is_verified: bool = False
    # If a newer clearance supersedes this one, set superseded_by.
    superseded_by: str | None = None


def _parse_ts(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def verify_clearance(
    clearance: GovernanceClearance | None,
    packet: dict[str, Any],
    now: datetime | None = None,
) -> ClearanceStatus:
    """Verify a REHT GovernanceClearance against the packet it authorizes.

    Returns a ClearanceStatus. Only VALID permits the execution boundary to
    return READY. Every other status fails closed.
    """
    if clearance is None:
        return ClearanceStatus.MISSING

    if not clearance.is_verified or not clearance.signature:
        return ClearanceStatus.UNVERIFIED

    if clearance.superseded_by:
        return ClearanceStatus.SUPERSEDED

    # Binding checks: the clearance must match the packet it claims to authorize.
    now = now or datetime.now(timezone.utc)

    issued = _parse_ts(clearance.issued_at)
    expires = _parse_ts(clearance.expires_at)
    if expires is not None and expires <= now:
        return ClearanceStatus.EXPIRED
    if issued is not None and issued > now:
        return ClearanceStatus.STALE
    if issued is not None and (now - issued).total_seconds() > MAX_CLEARANCE_AGE_SECONDS:
        return ClearanceStatus.STALE

    # Packet binding (anti-replay / mismatch).
    if clearance.packet_id != packet.get("packet_id"):
        return ClearanceStatus.MISMATCHED
    if clearance.policy_id != packet.get("policy", {}).get("policy_id"):
        return ClearanceStatus.MISMATCHED

    evidence = packet.get("evidence", {})
    fps = [
        s.get("hash")
        for s in evidence.get("sources", [])
        if isinstance(s, dict) and s.get("hash")
    ]
    fp = "|".join(sorted(fps))
    if fp and clearance.evidence_fingerprint and clearance.evidence_fingerprint != fp:
        return ClearanceStatus.MISMATCHED

    return ClearanceStatus.VALID
