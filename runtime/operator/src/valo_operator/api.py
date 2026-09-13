"""Stable, versioned Operator API contracts (frozen, extra='forbid').

The Operator's public entry surface. `submit()` takes a versioned
OperatorRequest and returns a versioned OperatorResult. The caller supplies a
correlation_id, the registered function identity and TYPED inputs — nothing
else (no effect/risk/authority/postconditions/idempotency overrides).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .actions import act
from .session import OperatorSession, validate_session

API_VERSION = "1.0"


class OperatorRequest(BaseModel):
    """A submission to the Operator. api_version must be supported; the
    correlation_id ties every result and future receipt to this submission."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    api_version: str = API_VERSION
    correlation_id: str = Field(min_length=1)
    function_id: str = Field(min_length=1)
    function_version: str = "1.0.0"
    inputs: dict[str, Any] = Field(default_factory=dict)


class OperatorResult(BaseModel):
    """The outcome of a submission. Never carries an effect/risk/authority
    override; the decision and permit are the boundary's, correlated to the
    correlation_id. When a session was submitted, its identity context is
    echoed back so the caller can attribute the outcome."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    api_version: str = API_VERSION
    correlation_id: str
    function_id: str
    status: str
    decision: str | None = None
    permit: str | None = None
    reason: str | None = None
    effect_verified: bool = False
    gateway_executions: int = 0
    errors: dict[str, str] = Field(default_factory=dict)
    tenant_id: str | None = None
    actor: str | None = None
    purpose_id: str | None = None
    instance_id: str | None = None
    receipts: list[dict[str, Any]] = Field(default_factory=list)


def submit(
    registry: Any,
    kernel_adapter: Any,
    reht: Any,
    gateway: Any,
    veritas: Any,
    baro: Any,
    request: OperatorRequest,
    session: OperatorSession | None = None,
) -> OperatorResult:
    """Submit a versioned OperatorRequest through the full boundary. The
    result is the boundary's, correlated to the request's correlation_id.

    An optional OperatorSession names the principal (tenant/actor/identity/
    purpose/delegation/step-up). The session is validated against Kernel truth
    BEFORE anything runs; the actor must match the registered Function's bound
    actor, and a rights-impacting Function requires session.step_up=True.
    Session violations return a REJECTED result, never a boundary decision."""
    if request.api_version != API_VERSION:
        raise ValueError(f"unsupported api_version {request.api_version!r}; supported: {API_VERSION}")

    if session is not None:
        violations = validate_session(kernel_adapter.engine, session)
        if violations:
            return OperatorResult(
                correlation_id=request.correlation_id,
                function_id=request.function_id,
                status="REJECTED",
                reason="; ".join(violations),
            )
        function_actor = _function_actor(registry, request.function_id, request.function_version)
        if session.actor != function_actor:
            return OperatorResult(
                correlation_id=request.correlation_id,
                function_id=request.function_id,
                status="REJECTED",
                reason=f"session actor {session.actor} does not match the registered Function actor {function_actor}",
            )
        definition = registry.resolve(request.function_id, request.function_version)
        if definition.risk_class.value == "R4_RIGHTS_IMPACTING" and not session.step_up:
            return OperatorResult(
                correlation_id=request.correlation_id,
                function_id=request.function_id,
                status="REJECTED",
                reason="rights-impacting Function requires session.step_up=True",
            )

    outcome = act(
        registry,
        kernel_adapter,
        reht,
        gateway,
        veritas,
        baro,
        function_id=request.function_id,
        version=request.function_version,
        inputs=request.inputs,
    )
    result = OperatorResult(
        correlation_id=request.correlation_id,
        function_id=outcome.function_id,
        status=outcome.status,
        decision=outcome.decision,
        permit=outcome.permit,
        reason=outcome.reason,
        effect_verified=outcome.effect_verified,
        gateway_executions=outcome.gateway_executions,
        errors=outcome.errors,
        instance_id=outcome.instance_id,
        receipts=outcome.receipts,
    )
    if session is not None:
        result = result.model_copy(
            update={"tenant_id": session.tenant_id, "actor": session.actor, "purpose_id": session.purpose_id}
        )
    return result


def _function_actor(registry: Any, function_id: str, version: str) -> str | None:
    """The actor the registered Function is bound to (from its workflow config)
    — the session principal must match it."""
    workflow = registry.graph_for(registry.get(f"{function_id}@{version}"))
    for node in workflow.nodes:
        if node.opcode == "EXECUTE_ACTION":
            return node.config.get("actor")
    return None
