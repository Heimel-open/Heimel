"""Deterministic operator actions.

The operator submits ONE registered Function (by FunctionRef + typed inputs).
The Function is resolved and COMPILED through Function Fabric, so effect type,
risk, authority requirement, requested-transition semantics, postconditions,
idempotency policy and typed inputs/outputs all come from the REGISTERED
Function contract — never from the operator caller.

The compiled workflow then runs the full boundary: pack pre-execution
admissibility -> fresh execution context -> REHT -> binding -> Gateway ->
Veritas -> BARO -> Kernel event. No own authorization, no own state machine,
no bypass of the Function Fabric contract surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from valo_function_fabric.compiler import compile_function_graph
from valo_function_fabric.contracts import (
    FunctionCall,
    FunctionGraph,
    FunctionRef,
)
from valo_workflow_isa import ReferenceBackend, RuntimeEngine


@dataclass
class ActionResult:
    function_id: str
    status: str
    decision: str | None = None
    permit: str | None = None
    reason: str | None = None
    gateway_executions: int = 0
    effect_verified: bool = False
    errors: dict[str, str] = field(default_factory=dict)
    instance_id: str | None = None
    receipts: list[dict[str, Any]] = field(default_factory=list)


def act(
    registry: Any,
    kernel_adapter: Any,
    reht: Any,
    gateway: Any,
    veritas: Any,
    baro: Any,
    *,
    function_id: str,
    version: str = "1.0.0",
    inputs: dict[str, Any] | None = None,
) -> ActionResult:
    """Submit one registered Function through the full boundary. Unknown
    function ids are rejected before anything runs; the caller supplies ONLY
    typed inputs — never effect/risk/authority/postconditions/idempotency."""
    definition = registry.resolve(function_id, version)

    graph_input_name = definition.input_type.name
    graph = FunctionGraph(
        graph_id="wf.operator.action", version="1",
        inputs={graph_input_name: definition.input_type.type},
        outputs={"out_final": definition.output_type.type},
        nodes=[
            FunctionCall(
                id="act",
                function_ref=FunctionRef(function_id=function_id, version=version),
                input_bindings={graph_input_name: graph_input_name},
                output_bindings={definition.output_type.name: "out_final"},
            )
        ],
        edges=[],
        entry_nodes=["act"],
        terminal_nodes=["act"],
    )
    compiled = compile_function_graph(graph, registry.snapshot())

    engine = RuntimeEngine(
        kernel_adapter, reht, gateway, veritas, baro,
        backend=ReferenceBackend(), tenant_id=kernel_adapter.tenant_id,
    )

    # correlate the decision to THIS instance: slice the REHT decision log at
    # the point this run started, so a reused REHT never reports a stale
    # decision from an earlier action.
    decisions_before = len(reht.decisions)
    executions_before = len(gateway.executions)
    instance = engine.start(compiled.workflow_graph, inputs or {})
    this_run = reht.decisions[decisions_before:]
    decision = this_run[-1] if this_run else None

    return ActionResult(
        function_id=function_id,
        status=instance.status.value,
        decision=decision.decision if decision else None,
        permit=decision.permit_ref if decision else None,
        reason=decision.reason if decision else None,
        gateway_executions=len(gateway.executions) - executions_before,
        effect_verified=_effect_verified(engine, instance),
        errors=instance.errors,
        instance_id=instance.instance_id,
        receipts=_receipts(engine, instance),
    )


def _effect_verified(engine: Any, instance: Any) -> bool:
    backend = engine.backend
    if backend is None:
        return False
    events = backend.events_for(instance.instance_id)
    return any(e.get("event_type") == "EffectVerified" for e in events)


def _receipts(engine: Any, instance: Any) -> list[dict[str, Any]]:
    """Operational receipts: the boundary events that PROVE what happened —
    authorization granted/denied, the action executed (external id), and the
    verified effect (receipt ref). Correlation is by instance_id."""
    backend = engine.backend
    if backend is None:
        return []
    receipts: list[dict[str, Any]] = []
    for event in backend.events_for(instance.instance_id):
        event_type = event.get("event_type")
        node_id = event.get("node_id")
        payload = event.get("payload") or {}
        if event_type == "AuthorizationGranted":
            receipts.append({"kind": "authorization", "decision": "ALLOW",
                            "clearance_ref": payload.get("clearance_ref"), "node": node_id})
        elif event_type == "AuthorizationDenied":
            receipts.append({"kind": "authorization", "decision": "DENY",
                            "reason": payload.get("reason"), "node": node_id})
        elif event_type == "ActionExecuted":
            receipts.append({"kind": "execution", "external_id": payload.get("external_id"),
                            "success": payload.get("success"), "node": node_id})
        elif event_type == "EffectVerified":
            receipts.append({"kind": "effect_verified",
                            "receipt_ref": payload.get("receipt_ref"), "node": node_id})
    return receipts
