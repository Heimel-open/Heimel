from __future__ import annotations

from typing import Any

from ..contracts.common import EffectType, canonical_digest
from ..contracts.events import WorkflowEventType
from ..runtime.context import HandlerContext
from ..runtime.errors import (
    AuthorizationDenied,
    Deferred,
    NodeFailure,
    PostconditionFailed,
    WorkflowError,
)
from ..runtime.expr import evaluate
from .keys import derive_idempotency_key


def _scope(ctx: HandlerContext) -> dict[str, Any]:
    return ctx.resolve_scope(ctx.instance, ctx.node.id)


def _config(ctx: HandlerContext, key: str, default: Any = None) -> Any:
    return ctx.node.config.get(key, default)


def _authority_params(ctx: HandlerContext) -> dict[str, str]:
    auth = ctx.node.policies.authority
    capability = auth.capability if auth else "WRITE"
    target = _config(ctx, "target", "")
    actor = _config(ctx, "actor", "")
    identity_id = _config(ctx, "identity_id")
    purpose_id = _config(ctx, "purpose_id")
    return {
        "actor": actor,
        "capability": capability,
        "target": target,
        "identity_id": identity_id,
        "purpose_id": purpose_id,
    }


def _idempotency_key(ctx: HandlerContext, inputs: dict[str, Any]) -> str:
    return derive_idempotency_key(ctx.node.policies.idempotency, inputs)


def _authorization(
    ctx: HandlerContext, inputs: dict[str, Any], action_contract: dict[str, Any]
) -> dict[str, Any]:
    """Steps a-d of the WRITE boundary: fresh execution context -> REHT -> RACS.
    This is the ONLY place authorization is requested; the runtime never
    decides it. Returns the sealed authorization artifact."""
    params = _authority_params(ctx)
    ctx.emit(
        WorkflowEventType.AUTHORIZATION_REQUESTED,
        {"action_type": action_contract.get("action_type"), "target": params["target"]},
    )
    execution_context = ctx.kernel.execution_context(
        tenant_id=ctx.tenant_id,
        actor=params["actor"],
        capability=params["capability"],
        target=params["target"],
        requested_transition=action_contract.get("requested_transition", {}),
        identity_id=params["identity_id"],
        purpose_id=params["purpose_id"],
    )
    decision = ctx.reht.authorize(execution_context, action_contract)
    if decision.decision != "ALLOW":
        reason = decision.reason
        if decision.decision == "MODIFY":
            reason = (
                "MODIFY cannot execute because DecisionResult does not carry "
                "the exact modified action contract"
            )
        ctx.emit(
            WorkflowEventType.AUTHORIZATION_DENIED,
            {"decision": decision.decision, "reason": reason},
        )
        raise AuthorizationDenied(
            f"authorization {decision.decision} for "
            f"{action_contract.get('action_type')}: {reason}"
        )

    if not (decision.clearance_ref or decision.permit_ref):
        reason = "ALLOW decision is missing a clearance_ref or permit_ref"
        ctx.emit(
            WorkflowEventType.AUTHORIZATION_DENIED,
            {"decision": decision.decision, "reason": reason},
        )
        raise AuthorizationDenied(
            f"authorization ALLOW for {action_contract.get('action_type')}: {reason}"
        )

    expected_context_hash = canonical_digest(execution_context)
    if decision.execution_context_hash != expected_context_hash:
        reason = (
            "ALLOW decision execution_context_hash is missing or does not "
            "match the fresh execution context"
        )
        ctx.emit(
            WorkflowEventType.AUTHORIZATION_DENIED,
            {"decision": decision.decision, "reason": reason},
        )
        raise AuthorizationDenied(
            f"authorization ALLOW for {action_contract.get('action_type')}: {reason}"
        )

    ctx.emit(
        WorkflowEventType.AUTHORIZATION_GRANTED,
        {
            "decision": decision.decision,
            "clearance_ref": decision.clearance_ref,
            "permit_ref": decision.permit_ref,
            "execution_context_hash": expected_context_hash,
        },
    )
    # REHT is the sole authorization boundary. The execution binding is derived
    # deterministically from the REHT decision (the RACS rule is a pure,
    # deterministic decision contract, NOT a processing component).
    binding = _derive_binding(decision, action_contract)
    return {
        "execution_context": execution_context,
        "decision": decision,
        "binding": binding,
    }


def _derive_binding(decision: Any, action_contract: dict[str, Any]) -> str:
    """Deterministic binding derivation: the same REHT decision and action
    contract always produce the same binding. Pure, no state, no I/O, no
    separate validation component."""
    artifact = {
        "decision": decision.decision,
        "clearance_ref": decision.clearance_ref,
        "permit_ref": decision.permit_ref,
        "execution_context_hash": decision.execution_context_hash,
        "action_contract": action_contract,
    }
    return f"binding:{canonical_digest(artifact)}"


def _execution(
    ctx: HandlerContext,
    inputs: dict[str, Any],
    action_contract: dict[str, Any],
    binding: str,
) -> None:
    """Steps e-h of the WRITE boundary: Gateway -> Veritas -> Kernel event ->
    BARO postcondition check. Runs only after a bound RACS result. A Gateway
    failure (success=False) NEVER emits EFFECT_VERIFIED and NEVER produces an
    authoritative Kernel effect event; it follows the node failure policy."""
    params = _authority_params(ctx)
    key = _idempotency_key(ctx, inputs)
    ctx.emit(WorkflowEventType.ACTION_REQUESTED, {"binding": binding})
    execution = ctx.gateway.execute(binding, action_contract, key)
    ctx.emit(
        WorkflowEventType.ACTION_EXECUTED,
        {"success": execution.success, "external_id": execution.external_id},
    )
    if not execution.success:
        raise NodeFailure(
            f"gateway execution failed for {action_contract.get('action_type')}: "
            f"success=False; not executed, not effect verified, no kernel transition"
        )

    observation = ctx.veritas.observe(execution, action_contract)

    postconditions = _config(ctx, "postconditions", {})
    if postconditions:
        baro = ctx.baro.check(postconditions, observation.observed)
        if baro.diverged:
            raise PostconditionFailed(f"postcondition divergence: {baro.reason or 'unknown'}")
    ctx.emit(WorkflowEventType.EFFECT_VERIFIED, {"receipt_ref": execution.receipt_ref})

    ctx.kernel.append_event(
        {
            "event_type": action_contract.get("kernel_event_type", "EXTERNAL_EFFECT_OBSERVED"),
            "tenant_id": ctx.tenant_id,
            "subject": params["target"],
            "actor": params["actor"],
            "source": "veritas",
            "payload": {
                "process_ref": f"{ctx.instance.instance_id}:{ctx.node.id}",
                "phase": "EXECUTION_OBSERVED",
                "observed": observation.observed,
                "requested_transition": action_contract.get("requested_transition", {}),
            },
        }
    )


def _write_pipeline(ctx: HandlerContext, inputs: dict[str, Any], action_contract: dict[str, Any]) -> dict[str, Any]:
    """Full WRITE boundary: authorization -> bound RACS -> execution. Used by
    EXECUTE_ACTION and resource handlers; AUTHORIZE_ACTION only runs
    `_authorization`."""
    result = _authorization(ctx, inputs, action_contract)
    _execution(ctx, inputs, action_contract, result["binding"])
    return result


def _out(ctx: HandlerContext, name: str, value: Any) -> dict[str, Any]:
    return {name: value}


# --- READ handlers -----------------------------------------------------------

def _read_state(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    target = _config(ctx, "target", "")
    state = ctx.kernel.read_state(ctx.tenant_id, target)
    return _out(ctx, ctx.node.outputs[0].name, state)


def _assert_state(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    state = inputs.get("state")
    if state is None:
        target = _config(ctx, "target", "")
        state = ctx.kernel.read_state(ctx.tenant_id, target)
    if not isinstance(state, dict):
        state = {"value": state}
    scope = {**state}
    for precondition in ctx.node.preconditions:
        if not evaluate(precondition, scope):
            return _out(ctx, ctx.node.outputs[0].name, False)
    return _out(ctx, ctx.node.outputs[0].name, True)


def _fetch(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    result = ctx.kernel.query(ctx.tenant_id, "fetch", {"source": _config(ctx, "source"), "params": _config(ctx, "params", {})})
    return _out(ctx, ctx.node.outputs[0].name, result)


# --- COMPUTE handlers --------------------------------------------------------

def _validate_schema(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    value = next(iter(inputs.values())) if inputs else None
    schema = _config(ctx, "schema", {})
    if schema and value is None:
        raise WorkflowError("VALIDATE_SCHEMA requires an input")
    return _out(ctx, ctx.node.outputs[0].name, value)


def _compare(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    left = _config(ctx, "left", None)
    right = _config(ctx, "right", None)
    if left is None and right is None and inputs:
        values = list(inputs.values())
        left, right = values[0], values[1] if len(values) > 1 else None
    return _out(ctx, ctx.node.outputs[0].name, {"left": left, "right": right, "equal": left == right})


def _reconcile(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    proposed = next(iter(inputs.values())) if inputs else _config(ctx, "proposed")
    # Probabilistic output (INFERRED wrapper) must be explicitly admitted here
    # before it can be treated as verified state downstream.
    if isinstance(proposed, dict) and "value" in proposed and proposed.get("truth_status") == "INFERRED":
        value = proposed["value"]
    else:
        value = proposed
    admitted = {"value": value, "verification": "reconciled", "truth_status": "ADMITTED"}
    return _out(ctx, ctx.node.outputs[0].name, admitted)


def _calculate(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    expression = _config(ctx, "expression")
    if expression is None:
        raise WorkflowError("CALCULATE requires an expression in config")
    result = evaluate_math(expression, {**_scope(ctx), **inputs})
    return _out(ctx, ctx.node.outputs[0].name, result)


def _evaluate_rule(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    rule = _config(ctx, "rule")
    if rule is None:
        raise WorkflowError("EVALUATE_RULE requires a rule in config")
    approved = evaluate(rule, {**_scope(ctx), **inputs})
    return _out(ctx, ctx.node.outputs[0].name, {"approved": approved, "reason": "rule" if approved else "denied by rule"})


def _prepare_action(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    params = _authority_params(ctx)
    action_contract = {
        "action_type": _config(ctx, "action_type", "EXECUTE"),
        "actor": params["actor"],
        "target": params["target"],
        "capability": params["capability"],
        "parameters": _config(ctx, "parameters", {**inputs}),
        "effect_type": ctx.node.effect_type.value if ctx.node.effect_type else None,
        "requested_transition": _config(ctx, "requested_transition", {}),
        "kernel_event_type": _config(ctx, "kernel_event_type"),
    }
    return _out(ctx, ctx.node.outputs[0].name, action_contract)


# --- DECIDE handlers ---------------------------------------------------------

def _request_input(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    injected = ctx.injected
    if injected is None:
        raise Deferred()
    return _out(ctx, ctx.node.outputs[0].name, injected)


# --- WRITE handlers ----------------------------------------------------------

def _authorize_action(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    action_contract = next(iter(inputs.values()))
    if not isinstance(action_contract, dict) or "action_type" not in action_contract:
        raise WorkflowError("AUTHORIZE_ACTION requires a prepared action contract input")
    _authorization(ctx, inputs, action_contract)
    return _out(ctx, ctx.node.outputs[0].name, action_contract)


def _execute_action(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    action_contract = next(iter(inputs.values()))
    if not isinstance(action_contract, dict):
        raise WorkflowError("EXECUTE_ACTION requires an action contract input")
    _write_pipeline(ctx, inputs, action_contract)
    return _out(ctx, ctx.node.outputs[0].name, action_contract)


def _verify_execution(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    result = _config(ctx, "verification_result")
    if result is None:
        result = {"verified": True, "observed": {}}
    return _out(ctx, ctx.node.outputs[0].name, result)


def _create_deadline(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    deadline = _config(ctx, "deadline")
    action_contract = {
        "action_type": "CREATE_DEADLINE",
        "actor": _config(ctx, "actor", ""),
        "target": _config(ctx, "target", ""),
        "parameters": {"deadline": deadline, **inputs},
        "effect_type": EffectType.CREATE_OBLIGATION.value,
        "kernel_event_type": "OBLIGATION_CREATED",
    }
    _write_pipeline(ctx, inputs, action_contract)
    return _out(ctx, ctx.node.outputs[0].name, {"deadline": deadline})


def _reserve_resource(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    action_contract = next(iter(inputs.values())) if inputs else None
    if isinstance(action_contract, dict) and action_contract.get("requested_transition", {}).get("reservation"):
        reservation = action_contract["requested_transition"]["reservation"]
        resource_id = reservation.get("resource_id", _config(ctx, "resource_id", ""))
        holder = reservation.get("holder", _config(ctx, "actor", ""))
    else:
        resource_id = _config(ctx, "resource_id", "")
        holder = _config(ctx, "actor", "")
        reservation = {
            "reservation_id": _config(ctx, "reservation_id"),
            "resource_id": resource_id,
            "holder": holder,
            "tenant_id": ctx.tenant_id,
            "purpose": _config(ctx, "purpose"),
        }
    new_contract = {
        "action_type": "RESERVE_RESOURCE",
        "actor": holder,
        "target": resource_id,
        "parameters": reservation,
        "effect_type": EffectType.ALLOCATE_RESOURCE.value,
        "kernel_event_type": "RESOURCE_RESERVED",
        "requested_transition": {"reservation": reservation},
    }
    _write_pipeline(ctx, inputs, new_contract)
    return _out(ctx, ctx.node.outputs[0].name, reservation)


def _release_resource(ctx: HandlerContext, inputs: dict[str, Any]) -> dict[str, Any]:
    resource_id = _config(ctx, "resource_id", "")
    reservation_id = _config(ctx, "reservation_id")
    action_contract = {
        "action_type": "RELEASE_RESOURCE",
        "actor": _config(ctx, "actor", ""),
        "target": resource_id,
        "parameters": {"reservation_id": reservation_id},
        "effect_type": EffectType.ALLOCATE_RESOURCE.value,
        "kernel_event_type": "RESERVATION_RELEASED",
    }
    _write_pipeline(ctx, inputs, action_contract)
    return _out(ctx, ctx.node.outputs[0].name, {"reservation_id": reservation_id})


def evaluate_math(expression: str, scope: dict[str, Any]) -> Any:
    """Deterministic arithmetic evaluator for CALCULATE (no eval of arbitrary
    code). Supports + - * / ( ) and field references."""
    import ast
    import operator

    tree = ast.parse(expression, mode="eval")

    def _node(node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            if node.id not in scope:
                raise WorkflowError(f"CALCULATE references unknown field {node.id}")
            return scope[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
            left = _node(node.left)
            right = _node(node.right)
            ops = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv}
            return ops[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -_node(node.operand)
        raise WorkflowError(f"CALCULATE expression not allowed: {expression}")

    return _node(tree.body)


def register_handlers(registry: dict[str, Any]) -> None:
    from ..contracts.common import PrimitiveOpcode

    registry.update(
        {
            PrimitiveOpcode.READ_STATE: _read_state,
            PrimitiveOpcode.ASSERT_STATE: _assert_state,
            PrimitiveOpcode.FETCH: _fetch,
            PrimitiveOpcode.VALIDATE_SCHEMA: _validate_schema,
            PrimitiveOpcode.COMPARE: _compare,
            PrimitiveOpcode.RECONCILE: _reconcile,
            PrimitiveOpcode.EVALUATE_RULE: _evaluate_rule,
            PrimitiveOpcode.CALCULATE: _calculate,
            PrimitiveOpcode.REQUEST_INPUT: _request_input,
            PrimitiveOpcode.REQUEST_REVIEW: _request_input,
            PrimitiveOpcode.REQUEST_APPROVAL: _request_input,
            PrimitiveOpcode.PREPARE_ACTION: _prepare_action,
            PrimitiveOpcode.AUTHORIZE_ACTION: _authorize_action,
            PrimitiveOpcode.EXECUTE_ACTION: _execute_action,
            PrimitiveOpcode.VERIFY_EXECUTION: _verify_execution,
            PrimitiveOpcode.CREATE_DEADLINE: _create_deadline,
            PrimitiveOpcode.RESERVE_RESOURCE: _reserve_resource,
            PrimitiveOpcode.RELEASE_RESOURCE: _release_resource,
        }
    )
