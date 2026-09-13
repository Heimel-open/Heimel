"""OperatorRuntime: a bound container of one pack's world.

It wires the registry, the Kernel adapter, the real REHT and the Gateway/
Veritas/BARO ports into one object the Operator API can call. Every deployment
surface (library, sidecar/service, HTTP gateway) shares THIS runtime — the
authorization chain is identical regardless of entry point.
"""

from __future__ import annotations

from typing import Any

from .actions import act
from .api import OperatorRequest, OperatorResult, submit
from .discovery import capabilities, discover_functions
from .evidence import EvidenceEntry, EvidenceLedger
from .session import OperatorSession
from .snapshot import operator_snapshot
from .views import kernel_views


class OperatorRuntime:
    """One pack's Operator runtime. Construct once, expose through any
    surface. Holds the world (kernel), so submissions advance it deterministically."""

    def __init__(
        self,
        *,
        pack_id: str,
        registry: Any,
        kernel_adapter: Any,
        reht: Any,
        gateway: Any,
        veritas: Any,
        baro: Any,
    ) -> None:
        self.pack_id = pack_id
        self.registry = registry
        self.kernel_adapter = kernel_adapter
        self.reht = reht
        self.gateway = gateway
        self.veritas = veritas
        self.baro = baro
        self.ledger = EvidenceLedger()

    @property
    def kernel(self) -> Any:
        return self.kernel_adapter.engine

    def submit(self, request: OperatorRequest, session: OperatorSession | None = None) -> OperatorResult:
        result = submit(
            self.registry, self.kernel_adapter, self.reht,
            self.gateway, self.veritas, self.baro, request, session=session,
        )
        self.ledger.record(request.correlation_id, _outcome_from_result(result), baro_outcome=_baro_outcome(result))
        return result

    def evidence(self) -> list[EvidenceEntry]:
        return self.ledger.entries

    def evidence_by_correlation(self, correlation_id: str) -> EvidenceEntry | None:
        return self.ledger.by_correlation_id(correlation_id)

    def audit(self, function_id: str | None = None, status: str | None = None) -> list[EvidenceEntry]:
        entries = self.ledger.entries
        if function_id is not None:
            entries = [e for e in entries if e.function_id == function_id]
        if status is not None:
            entries = [e for e in entries if e.status == status]
        return entries

    def views(self) -> dict[str, Any]:
        return kernel_views(self.kernel)

    def snapshot(self) -> dict[str, Any]:
        return operator_snapshot(self.kernel, pack_id=self.pack_id)

    def discover(self) -> list[dict[str, Any]]:
        return discover_functions(self.registry)

    def capabilities(self) -> list[str]:
        return capabilities(self.registry)

    def act_raw(self, function_id: str, version: str = "1.0.0", inputs: dict[str, Any] | None = None) -> Any:

        return act(
            self.registry, self.kernel_adapter, self.reht,
            self.gateway, self.veritas, self.baro,
            function_id=function_id, version=version, inputs=inputs,
        )


def _outcome_from_result(result: Any) -> Any:
    from .actions import ActionResult

    return ActionResult(
        function_id=result.function_id,
        status=result.status,
        decision=result.decision,
        permit=result.permit,
        reason=result.reason,
        gateway_executions=result.gateway_executions,
        effect_verified=result.effect_verified,
        errors=result.errors,
        instance_id=result.instance_id,
        receipts=result.receipts,
    )


def _baro_outcome(result: Any) -> str:
    if result.status == "COMPLETED":
        return "ok"
    if any("postcondition divergence" in message for message in (result.errors or {}).values()):
        return "diverged"
    return "not_checked"
