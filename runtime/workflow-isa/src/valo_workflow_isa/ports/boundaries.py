from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class DecisionResult:
    decision: str  # ALLOW | MODIFY | DEFER | DENY | STEP_UP | HALT
    clearance_ref: str | None = None
    permit_ref: str | None = None
    execution_context_hash: str | None = None
    reason: str | None = None


@dataclass(frozen=True)
class ExecutionResult:
    success: bool
    external_id: str | None = None
    receipt_ref: str | None = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Observation:
    phase: str  # EXECUTION_OBSERVED etc.
    observed: dict[str, Any] = field(default_factory=dict)
    receipt_ref: str | None = None


@dataclass(frozen=True)
class BaroResult:
    diverged: bool
    reason: str | None = None
    expected: dict[str, Any] = field(default_factory=dict)
    observed: dict[str, Any] = field(default_factory=dict)


class KernelPort(Protocol):
    """Typed Kernel queries. Workflow ISA never receives a mutable WorldState;
    every read returns immutable data."""

    def read_state(self, tenant_id: str, entity_id: str) -> dict[str, Any]: ...

    def query(self, tenant_id: str, query_type: str, params: dict[str, Any]) -> dict[str, Any]: ...

    def execution_context(
        self,
        tenant_id: str,
        actor: str,
        capability: str,
        target: str,
        requested_transition: dict[str, Any],
        identity_id: str | None = None,
        purpose_id: str | None = None,
    ) -> dict[str, Any]: ...

    def append_event(self, event: dict[str, Any]) -> dict[str, Any]: ...


class RehtPort(Protocol):
    def authorize(self, execution_context: dict[str, Any], action_contract: dict[str, Any]) -> DecisionResult: ...


class GatewayPort(Protocol):
    def execute(self, binding: str, action_contract: dict[str, Any], idempotency_key: str) -> ExecutionResult:
        """Execute against the artifact named by the execution binding. The
        binding is derived deterministically from the REHT decision (the RACS
        rule is a pure decision contract, not a component); it is never a raw
        REHT decision. The Gateway is the only place the external call happens."""

    def has_effect(self, idempotency_key: str) -> bool:
        """True when the external boundary already produced an effect for this
        idempotency key. Used to decide replay vs. fresh execution."""
        ...


class VeritasPort(Protocol):
    def observe(self, execution: ExecutionResult, action_contract: dict[str, Any]) -> Observation: ...


class BaroPort(Protocol):
    def check(self, expected: dict[str, Any], observed: dict[str, Any]) -> BaroResult: ...
