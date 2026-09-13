"""Operational evidence: a queryable audit ledger of Operator submissions.

Every submission produces an EvidenceEntry tied to the caller's
correlation_id and the workflow instance_id, carrying the decision, permit,
effect-verified flag, BARO outcome and the operational receipts. The ledger is
append-only and queryable.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .actions import ActionResult

_UTC = UTC


class EvidenceEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    correlation_id: str
    instance_id: str
    function_id: str
    status: str
    decision: str | None = None
    permit: str | None = None
    reason: str | None = None
    effect_verified: bool = False
    gateway_executions: int = 0
    baro_outcome: str = "ok"  # ok | diverged | not_checked
    receipts: list[dict[str, Any]] = Field(default_factory=list)
    recorded_at: str = Field(default_factory=lambda: datetime.now(_UTC).isoformat())


class EvidenceLedger:
    """Append-only audit log. Queries are read-only and deterministic on the
    recorded entries."""

    def __init__(self) -> None:
        self._entries: list[EvidenceEntry] = []
        self._by_correlation: dict[str, EvidenceEntry] = {}

    def record(self, correlation_id: str, outcome: ActionResult, baro_outcome: str = "ok") -> EvidenceEntry:
        entry = EvidenceEntry(
            correlation_id=correlation_id,
            instance_id=outcome.instance_id or "",
            function_id=outcome.function_id,
            status=outcome.status,
            decision=outcome.decision,
            permit=outcome.permit,
            reason=outcome.reason,
            effect_verified=outcome.effect_verified,
            gateway_executions=outcome.gateway_executions,
            baro_outcome=baro_outcome,
            receipts=outcome.receipts,
        )
        self._entries.append(entry)
        self._by_correlation[correlation_id] = entry
        return entry

    @property
    def entries(self) -> list[EvidenceEntry]:
        return list(self._entries)

    def by_correlation_id(self, correlation_id: str) -> EvidenceEntry | None:
        return self._by_correlation.get(correlation_id)

    def by_function(self, function_id: str) -> list[EvidenceEntry]:
        return [e for e in self._entries if e.function_id == function_id]

    def by_status(self, status: str) -> list[EvidenceEntry]:
        return [e for e in self._entries if e.status == status]

    def latest(self, limit: int = 10) -> list[EvidenceEntry]:
        return list(self._entries[-limit:])

    def clear(self) -> None:
        self._entries.clear()
        self._by_correlation.clear()
