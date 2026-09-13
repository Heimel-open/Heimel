"""Admit Veritas-verified execution outcomes into Kernel history.

The external effect already happened elsewhere. Kernel only records the verified
observation as append-only state history. The observation cannot grant, extend,
or recreate authority.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any, Mapping

from ..contracts.events import CanonicalEvent, EventType
from .engine import KernelEngine

_ALLOWED_STATUS = {
    "BLOCKED",
    "NOT_COMMITTED",
    "FAILED",
    "COMMITTED",
    "COMMITTED_UNVERIFIED",
    "COMMITTED_WITH_DEVIATION",
}
_ALLOWED_REHT = {None, "ALLOW", "STEP_UP", "DENY"}


@dataclass(frozen=True)
class VerifiedExecutionOutcomeV1:
    receipt_id: str
    veritas_ref: str
    status: str
    action_digest: str
    execution_context_hash: str | None
    reht_decision: str | None
    clearance_ref: str | None
    permit_ref: str | None
    effect_result_digest: str | None
    observed_at: str
    postconditions_verified: bool | None = None
    authority_granted: bool = False

    def __post_init__(self) -> None:
        if not self.receipt_id.startswith("sha256:"):
            raise ValueError("receipt_id must be a sha256 reference")
        if not self.veritas_ref:
            raise ValueError("Veritas WORM reference is required")
        if self.status not in _ALLOWED_STATUS:
            raise ValueError("unsupported execution outcome status")
        if self.reht_decision not in _ALLOWED_REHT:
            raise ValueError("unsupported REHT decision")
        if self.authority_granted:
            raise ValueError("execution outcome evidence cannot grant authority")
        try:
            parsed = datetime.fromisoformat(self.observed_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("observed_at must be ISO-8601") from exc
        if parsed.tzinfo is None:
            raise ValueError("observed_at must be timezone-aware")
        if self.reht_decision == "ALLOW" and (
            not self.clearance_ref or not self.permit_ref
        ):
            raise ValueError("REHT ALLOW outcome requires clearance and permit")

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)


class KernelExecutionOutcomeConsumer:
    """Concrete consumer used after Veritas has admitted an execution receipt."""

    def __init__(self, engine: KernelEngine) -> None:
        self._engine = engine

    def append_verified_execution_outcome(
        self,
        outcome: VerifiedExecutionOutcomeV1 | Mapping[str, Any],
    ) -> str:
        verified = (
            outcome
            if isinstance(outcome, VerifiedExecutionOutcomeV1)
            else VerifiedExecutionOutcomeV1(**dict(outcome))
        )
        observed_at = datetime.fromisoformat(
            verified.observed_at.replace("Z", "+00:00")
        ).astimezone(UTC)
        stable = verified.receipt_id.removeprefix("sha256:")
        event = CanonicalEvent(
            event_id=f"execution-outcome:{stable}",
            event_type=EventType.EXTERNAL_EFFECT_OBSERVED,
            tenant_id=self._engine.tenant_id,
            subject=verified.action_digest,
            timestamp=observed_at,
            effective_at=observed_at,
            source="veritas",
            payload={
                "verified_execution_outcome": verified.to_payload(),
                "verification_basis": "VERITAS_WORM",
                "authority_granted": False,
            },
            evidence_refs=[verified.veritas_ref],
            causation_id=verified.clearance_ref,
            correlation_id=verified.permit_ref,
            idempotency_key=verified.receipt_id,
        )
        sealed = self._engine.append(event)
        return sealed.event_hash or sealed.event_id


__all__ = [
    "KernelExecutionOutcomeConsumer",
    "VerifiedExecutionOutcomeV1",
]
