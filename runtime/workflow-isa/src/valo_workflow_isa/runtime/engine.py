from __future__ import annotations

from typing import Any

from ..compiler.compiler import compile_graph
from ..contracts.common import (
    ControlOpcode,
    Determinism,
    EdgeType,
    NodeClass,
    NodeStatus,
    PrimitiveOpcode,
    WorkflowStatus,
    canonical_digest,
)
from ..contracts.events import WorkflowEvent, WorkflowEventType
from ..contracts.graph import WorkflowEdge, WorkflowGraph, WorkflowNode
from ..ports.boundaries import (
    BaroPort,
    GatewayPort,
    KernelPort,
    RehtPort,
    VeritasPort,
)
from ..ports.runtime_backend import RuntimeBackend
from ..stdlib.handlers import register_handlers
from .context import HandlerContext
from .errors import (
    AuthorizationDenied,
    Deferred,
    NodeFailure,
    NodeTimeout,
    PostconditionFailed,
    TypeViolation,
    WorkflowError,
)
from .expr import evaluate
from .instance import WorkflowInstance

MAX_STEPS = 10000


class RuntimeEngine:
    """Deterministic in-memory reference runtime. The durable backend contract
    (RuntimeBackend) is the seam a Temporal backend can implement later."""

    def __init__(
        self,
        kernel: KernelPort,
        reht: RehtPort,
        gateway: GatewayPort,
        veritas: VeritasPort,
        baro: BaroPort,
        backend: RuntimeBackend | None = None,
        child_graphs: dict[str, WorkflowGraph] | None = None,
        tenant_id: str = "default",
    ) -> None:
        self.kernel = kernel
        self.reht = reht
        self.gateway = gateway
        self.veritas = veritas
        self.baro = baro
        self.backend = backend
        self.child_graphs = dict(child_graphs or {})
        self.tenant_id = tenant_id
        self.handlers: dict[str, Any] = {}
        register_handlers(self.handlers)
        self._compiled_graphs: set[str] = set()

    # --- public API ----------------------------------------------------------

    def start(
        self,
        graph: WorkflowGraph,
        inputs: dict[str, Any] | None = None,
        *,
        correlation_id: str | None = None,
        parent_instance_id: str | None = None,
    ) -> WorkflowInstance:
        self._ensure_compiled(graph)
        instance = WorkflowInstance(
            graph=graph,
            input_values=dict(inputs or {}),
            correlation_id=correlation_id,
            parent_instance_id=parent_instance_id,
        )
        instance.input_values.setdefault("__tenant", self.tenant_id)
        instance.init_node_states()
        self._emit(
            instance,
            WorkflowEventType.WORKFLOW_STARTED,
            node_id=graph.entry,
            payload={"inputs": {k: _summarize(v) for k, v in (inputs or {}).items()}},
        )
        return self.run(instance)

    def resume(self, instance: WorkflowInstance, values: dict[str, Any]) -> WorkflowInstance:
        """Provide deferred input and continue execution."""
        self._ensure_compiled(instance.graph)
        resumable_opcodes = {
            ControlOpcode.WAIT.value,
            PrimitiveOpcode.REQUEST_INPUT.value,
            PrimitiveOpcode.REQUEST_REVIEW.value,
            PrimitiveOpcode.REQUEST_APPROVAL.value,
        }
        node_map = instance.graph.node_map()
        for node_id, status in instance.node_statuses.items():
            if (
                status == NodeStatus.DEFERRED
                and node_map[node_id].opcode in resumable_opcodes
            ):
                instance.deferred_inputs[node_id] = values
                instance.node_statuses[node_id] = NodeStatus.PENDING
                instance.deferred_until_input = False
        return self.run(instance)

    def run(self, instance: WorkflowInstance) -> WorkflowInstance:
        self._ensure_compiled(instance.graph)
        if instance.status in (WorkflowStatus.COMPLETED, WorkflowStatus.FAILED, WorkflowStatus.HALTED):
            return instance
        instance.status = WorkflowStatus.RUNNING
        steps = 0
        while True:
            steps += 1
            if steps > MAX_STEPS:
                return self._fail(instance, "runtime exceeded MAX_STEPS", NodeStatus.FAILED)
            if instance.halt_reason:
                instance.status = WorkflowStatus.HALTED
                self._emit(instance, WorkflowEventType.WORKFLOW_HALTED, payload={"reason": instance.halt_reason})
                self._persist(instance)
                return instance

            self._mark_skipped(instance)
            ready = self._ready_nodes(instance)
            if not ready:
                if any(s == NodeStatus.DEFERRED for s in instance.node_statuses.values()):
                    instance.status = WorkflowStatus.DEFERRED
                    instance.deferred_until_input = True
                    self._persist(instance)
                    return instance
                if self._all_terminals_done(instance):
                    instance.status = WorkflowStatus.COMPLETED
                    self._emit(instance, WorkflowEventType.WORKFLOW_COMPLETED, node_id=instance.graph.entry)
                    self._persist(instance)
                    return instance
                return self._fail(instance, "no ready nodes and terminals not reached", NodeStatus.FAILED)

            for node_id in sorted(ready):
                self._execute_node(instance, node_id)
                if instance.halt_reason:
                    break
                if instance.status in (WorkflowStatus.FAILED, WorkflowStatus.HALTED, WorkflowStatus.DEFERRED):
                    break
            self._persist(instance)
            if instance.status in (
                WorkflowStatus.FAILED,
                WorkflowStatus.HALTED,
                WorkflowStatus.DEFERRED,
                WorkflowStatus.COMPLETED,
            ):
                return instance

    # --- readiness -----------------------------------------------------------

    def _ready_nodes(self, instance: WorkflowInstance) -> list[str]:
        ready: list[str] = []
        graph = instance.graph
        for node in graph.nodes:
            if instance.node_statuses[node.id] != NodeStatus.PENDING:
                continue
            incoming = [e for e in graph.edges if e.target == node.id]
            if all(self._edge_fires(instance, edge) for edge in incoming):
                ready.append(node.id)
        return ready

    def _edge_fires(self, instance: WorkflowInstance, edge: WorkflowEdge) -> bool:
        src_status = instance.node_statuses[edge.source]
        if edge.edge_type in (EdgeType.NEXT, EdgeType.TRUE, EdgeType.FALSE):
            if src_status != NodeStatus.COMPLETED:
                return False
            if edge.condition:
                return evaluate(edge.condition, instance.outputs.get(edge.source, {}))
            outputs = instance.outputs.get(edge.source, {})
            truthy = bool(next(iter(outputs.values()), None)) if outputs else False
            if edge.edge_type == EdgeType.TRUE:
                return truthy
            if edge.edge_type == EdgeType.FALSE:
                return not truthy
            return True
        if edge.edge_type == EdgeType.ERROR:
            return src_status == NodeStatus.FAILED
        if edge.edge_type == EdgeType.TIMEOUT:
            return src_status == NodeStatus.FAILED and instance.errors.get(edge.source) == "timeout"
        if edge.edge_type == EdgeType.COMPENSATE:
            return instance.compensating
        return False

    def _edge_can_fire(self, instance: WorkflowInstance, edge: WorkflowEdge) -> bool:
        """Whether an edge may still fire. A PENDING/RUNNING/DEFERRED source may
        still complete; a SKIPPED source never fires; a COMPLETED source fires
        only if its condition selects it; a FAILED source only fires ERROR/
        TIMEOUT edges."""
        src_status = instance.node_statuses[edge.source]
        if src_status in (NodeStatus.PENDING, NodeStatus.RUNNING, NodeStatus.DEFERRED):
            return True
        if src_status in (NodeStatus.SKIPPED, NodeStatus.COMPENSATED):
            return False
        if src_status == NodeStatus.FAILED:
            return edge.edge_type in (EdgeType.ERROR, EdgeType.TIMEOUT)
        if src_status == NodeStatus.COMPLETED:
            return self._edge_fires(instance, edge)
        return False

    def _mark_skipped(self, instance: WorkflowInstance) -> None:
        """Path semantics: a node whose incoming edges can never fire is marked
        SKIPPED (e.g. the non-selected arm of a TRUE/FALSE branch). Iterates to
        a fixpoint so skipped branches propagate downstream. This is what makes
        alternative terminals resolvable: the workflow completes when the
        SELECTED path reaches a terminal, not when every alternative executes."""
        changed = True
        while changed:
            changed = False
            graph = instance.graph
            for node in graph.nodes:
                if instance.node_statuses[node.id] != NodeStatus.PENDING:
                    continue
                incoming = [e for e in graph.edges if e.target == node.id]
                if not incoming:
                    continue  # entry node is never skipped
                if all(not self._edge_can_fire(instance, edge) for edge in incoming):
                    instance.node_statuses[node.id] = NodeStatus.SKIPPED
                    changed = True

    def _all_terminals_done(self, instance: WorkflowInstance) -> bool:
        if not instance.graph.terminal_states:
            return True
        statuses = [instance.node_statuses.get(t) for t in instance.graph.terminal_states]
        return NodeStatus.COMPLETED in statuses and all(
            s in (NodeStatus.COMPLETED, NodeStatus.SKIPPED) for s in statuses
        )

    # --- node execution ------------------------------------------------------

    def _execute_node(self, instance: WorkflowInstance, node_id: str) -> None:
        node = instance.graph.node_map()[node_id]
        instance.node_statuses[node_id] = NodeStatus.RUNNING
        instance.attempts[node_id] = instance.attempts.get(node_id, 0) + 1
        self._emit(instance, WorkflowEventType.NODE_STARTED, node_id=node_id, attempt=instance.attempts[node_id])

        ctx = self._handler_context(instance, node)
        try:
            self._enforce_timeout(node)
            if node.opcode in set(ControlOpcode):
                outputs = self._run_control(ctx, node)
            else:
                inputs = self._resolve_inputs(instance, node)
                handler = self.handlers.get(node.opcode)
                if handler is None:
                    raise NodeFailure(f"no handler for opcode {node.opcode}")
                outputs = handler(ctx, inputs)
            outputs = self._wrap_probabilistic(node, outputs)
            outputs = self._finalize_outputs(node, outputs, instance)
            instance.outputs[node_id] = outputs
            instance.node_statuses[node_id] = NodeStatus.COMPLETED
            instance.completion_order.append(node_id)
            self._emit(instance, WorkflowEventType.NODE_COMPLETED, node_id=node_id, attempt=instance.attempts[node_id])
        except Deferred:
            instance.node_statuses[node_id] = NodeStatus.DEFERRED
            self._emit(instance, WorkflowEventType.NODE_DEFERRED, node_id=node_id)
            instance.deferred_until_input = True
        except (AuthorizationDenied, PostconditionFailed, NodeFailure, WorkflowError, NodeTimeout) as exc:
            self._handle_node_failure(instance, node, str(exc))
        except Exception as exc:  # fail closed: any unexpected handler error fails the node
            self._handle_node_failure(instance, node, f"unexpected error: {exc}")

    def _run_control(self, ctx: HandlerContext, node: WorkflowNode) -> dict[str, Any]:
        opcode = node.opcode
        if opcode in (ControlOpcode.SEQ.value, ControlOpcode.PARALLEL.value, ControlOpcode.JOIN.value, ControlOpcode.RETRY.value):
            return {node.outputs[0].name: True} if node.outputs else {}
        if opcode in (ControlOpcode.BRANCH.value, ControlOpcode.LOOP.value):
            condition = node.config.get("condition", "true")
            result = evaluate(condition, self._scope(instance_of(ctx)))
            name = node.outputs[0].name if node.outputs else "result"
            return {name: result}
        if opcode == ControlOpcode.WAIT.value:
            if ctx.injected is not None:
                return {node.outputs[0].name: ctx.injected} if node.outputs else {}
            raise Deferred()
        if opcode == ControlOpcode.TIMEOUT.value:
            if node.timeout and node.timeout < 0:
                raise NodeTimeout(f"timeout on {node.id}")
            return {node.outputs[0].name: True} if node.outputs else {}
        if opcode == ControlOpcode.COMPENSATE.value:
            return {node.outputs[0].name: True} if node.outputs else {}
        if opcode == ControlOpcode.CALL.value:
            return self._run_call(ctx, node)
        if opcode == ControlOpcode.RETURN.value:
            value = node.config.get("value")
            return {node.outputs[0].name: value} if node.outputs else {}
        if opcode == ControlOpcode.HALT.value:
            ctx.instance.halt_reason = node.config.get("reason", "halt")
            return {}
        raise NodeFailure(f"unhandled control opcode {opcode}")

    def _run_call(self, ctx: HandlerContext, node: WorkflowNode) -> dict[str, Any]:
        child_graph = self.child_graphs.get(node.config.get("graph_id"))
        if child_graph is None:
            raise NodeFailure(f"CALL references unknown child graph {node.config.get('graph_id')}")
        self._ensure_compiled(child_graph)
        child_inputs = {k: v for k, v in self._scope(ctx.instance).items() if k in child_graph.input_schema}
        child = self.start(
            child_graph,
            child_inputs,
            correlation_id=ctx.instance.correlation_id,
            parent_instance_id=ctx.instance.instance_id,
        )
        ctx.instance.call_stack.append(child.instance_id)
        if child.status == WorkflowStatus.COMPLETED:
            out_name = node.outputs[0].name if node.outputs else "result"
            child_outputs: dict[str, Any] = {}
            for nid in child.completion_order:
                child_outputs.update(child.outputs.get(nid, {}))
            return {out_name: child_outputs}
        raise NodeFailure(f"child workflow {child.instance_id} {child.status.value}")

    def _enforce_timeout(self, node: WorkflowNode) -> None:
        if node.timeout is not None and node.timeout < 0:
            raise NodeTimeout(f"timeout on {node.id}")

    def _wrap_probabilistic(self, node: WorkflowNode, outputs: dict[str, Any]) -> dict[str, Any]:
        if node.determinism != Determinism.PROBABILISTIC:
            return outputs
        wrapped: dict[str, Any] = {}
        for name, value in outputs.items():
            wrapped[name] = {
                "value": value,
                "model": node.config.get("model"),
                "model_version": node.config.get("model_version"),
                "confidence": node.config.get("confidence"),
                "source_context": node.config.get("source_context"),
                "truth_status": "INFERRED",
            }
        return wrapped

    def _finalize_outputs(self, node: WorkflowNode, outputs: dict[str, Any], instance: WorkflowInstance) -> dict[str, Any]:
        """Attach and enforce runtime refinements. A refined output type must be
        satisfiable by a RuntimeValue that provably carries the refinement; the
        runtime fails closed otherwise. Only producers whose opcode semantics
        legitimately produce the refinement may attach it (the WRITE boundary
        verified the effect; RECONCILE/PREPARE_ACTION/VALIDATE_SCHEMA/
        VERIFY_EXECUTION verified or prepared the value)."""
        from ..types.system import parse_type
        from .values import RuntimeValue

        attachable = _attachable_refinements(node)
        finalized: dict[str, Any] = {}
        for ref in node.outputs:
            if ref.name not in outputs:
                raise NodeFailure(f"node {node.id} did not produce output {ref.name}")
            declared = parse_type(ref.type)
            value = outputs[ref.name]
            if not declared.refinements:
                finalized[ref.name] = value
                continue
            if not declared.refinements.issubset(attachable):
                raise TypeViolation(
                    f"node {node.id} output {ref.name}: declared refinements "
                    f"{sorted(declared.refinements)} are not producible by opcode {node.opcode} "
                    f"(attachable {sorted(attachable)})"
                )
            finalized[ref.name] = RuntimeValue(
                value=value,
                base_type=declared.base,
                refinements=declared.refinements,
                receipt_refs=[_receipt(value)] if node.node_class in (NodeClass.WRITE,) else [],
            )
        return finalized

    def _handle_node_failure(self, instance: WorkflowInstance, node: WorkflowNode, message: str) -> None:
        instance.node_statuses[node.id] = NodeStatus.FAILED
        instance.errors[node.id] = message
        self._emit(instance, WorkflowEventType.NODE_FAILED, node_id=node.id, attempt=instance.attempts[node.id], payload={"message": message})

        policy = node.policies.retry
        if policy.max_attempts > 1 and instance.attempts[node.id] < policy.max_attempts:
            if self._retry_requires_verify(node):
                effect_exists = self._effect_already_exists(instance, node)
                if effect_exists is not False:
                    reason = (
                        "external effect reported; independent verification and "
                        "reconciliation required before continuation"
                        if effect_exists
                        else "external effect status unavailable; independent "
                        "verification and reconciliation required before retry"
                    )
                    instance.node_statuses[node.id] = NodeStatus.DEFERRED
                    instance.status = WorkflowStatus.DEFERRED
                    instance.deferred_until_input = True
                    instance.errors[node.id] = reason
                    self._emit(
                        instance,
                        WorkflowEventType.NODE_DEFERRED,
                        node_id=node.id,
                        attempt=instance.attempts[node.id],
                        payload={"reason": reason, "outcome_known": False},
                    )
                    return
            instance.node_statuses[node.id] = NodeStatus.PENDING
            return

        if instance.graph.failure_policy == "HALT" or node.config.get("halt_on_failure"):
            instance.halt_reason = f"{node.id}: {message}"
            self._emit(instance, WorkflowEventType.WORKFLOW_HALTED, node_id=node.id, payload={"reason": instance.halt_reason})
            return
        if instance.graph.failure_policy == "COMPENSATE":
            instance.compensating = True
            self._run_compensation(instance)
            return
        if instance.graph.failure_policy == "DEFER":
            instance.status = WorkflowStatus.DEFERRED
            return
        instance.status = WorkflowStatus.FAILED
        self._emit(instance, WorkflowEventType.WORKFLOW_FAILED, node_id=node.id, payload={"message": message})

    def _retry_requires_verify(self, node: WorkflowNode) -> bool:
        from ..effects.system import IRREVERSIBLE_EFFECTS

        return (
            node.node_class == NodeClass.WRITE
            and node.effect_type in IRREVERSIBLE_EFFECTS
            and (node.policies.idempotency.verify_before_replay or node.policies.retry.retry_after_timeout)
        )

    def _effect_already_exists(
        self, instance: WorkflowInstance, node: WorkflowNode
    ) -> bool | None:
        """Check whether the external boundary already produced an effect for
        this node's idempotency key (verification/reconciliation before replay).
        True is detection only, not verified completion. None means the check
        itself could not be established, so replay must also fail closed."""
        from ..stdlib.keys import derive_idempotency_key

        inputs = self._resolve_inputs(instance, node)
        key = derive_idempotency_key(node.policies.idempotency, inputs)
        if not key:
            return None
        try:
            return bool(self.gateway.has_effect(key))
        except Exception:
            return None

    def _run_compensation(self, instance: WorkflowInstance) -> None:
        instance.compensating = True
        to_compensate = [
            nid for nid in reversed(instance.completion_order) if instance.graph.node_map()[nid].compensation_ref
        ]
        for nid in to_compensate:
            comp_ref = instance.graph.node_map()[nid].compensation_ref
            comp_node = instance.graph.node_map().get(comp_ref)
            if comp_node is None:
                continue
            self._emit(instance, WorkflowEventType.COMPENSATION_STARTED, node_id=comp_ref, payload={"for_node": nid})
            ctx = self._handler_context(instance, comp_node)
            inputs = self._resolve_inputs(instance, comp_node)
            handler = self.handlers.get(comp_node.opcode)
            if handler is None:
                continue
            try:
                outputs = handler(ctx, inputs)
                instance.outputs[comp_ref] = outputs
                instance.node_statuses[comp_ref] = NodeStatus.COMPENSATED
            except WorkflowError:
                instance.node_statuses[comp_ref] = NodeStatus.FAILED
        instance.status = WorkflowStatus.FAILED
        instance.errors["__compensation__"] = "compensated"

    # --- helpers -------------------------------------------------------------

    def _resolve_inputs(self, instance: WorkflowInstance, node: WorkflowNode) -> dict[str, Any]:
        scope = self._scope(instance)
        resolved: dict[str, Any] = {}
        for ref in node.inputs:
            if ref.name in scope:
                value = scope[ref.name]
                resolved[ref.name] = _unwrap(value)
        return resolved

    def _scope(self, instance: WorkflowInstance) -> dict[str, Any]:
        scope: dict[str, Any] = dict(instance.input_values)
        for nid in instance.completion_order:
            scope.update(instance.outputs.get(nid, {}))
        return scope

    def _handler_context(self, instance: WorkflowInstance, node: WorkflowNode) -> HandlerContext:
        return HandlerContext(
            instance=instance,
            node=node,
            graph=instance.graph,
            kernel=self.kernel,
            reht=self.reht,
            gateway=self.gateway,
            veritas=self.veritas,
            baro=self.baro,
            emit=lambda event: self._emit(instance, event.event_type, node_id=event.node_id, attempt=event.attempt, payload=event.payload),
            resolve_scope=lambda _i, _n: self._scope(_i),
            run_child=self._run_call,
        )

    def _emit(self, instance: WorkflowInstance, event_type: WorkflowEventType, node_id: str | None = None, attempt: int = 1, payload: dict[str, Any] | None = None) -> None:
        event = WorkflowEvent(
            event_type=event_type,
            workflow_instance_id=instance.instance_id,
            graph_id=instance.graph.id,
            graph_version=instance.graph.version,
            node_id=node_id,
            attempt=attempt,
            correlation_id=instance.correlation_id,
            payload=payload or {},
        )
        if self.backend is not None:
            self.backend.append_event(event.model_dump(mode="json"))

    def _persist(self, instance: WorkflowInstance) -> None:
        instance.touch()
        if self.backend is not None:
            self.backend.save_instance(instance.serialize())

    def _fail(self, instance: WorkflowInstance, message: str, node_status: NodeStatus) -> WorkflowInstance:
        instance.status = WorkflowStatus.FAILED
        instance.errors["__runtime__"] = message
        self._emit(instance, WorkflowEventType.WORKFLOW_FAILED, payload={"message": message})
        self._persist(instance)
        return instance

    def _ensure_compiled(self, graph: WorkflowGraph) -> None:
        graph_digest = canonical_digest(graph.model_dump(mode="json"))
        if graph_digest in self._compiled_graphs:
            return
        compile_graph(graph)
        self._compiled_graphs.add(graph_digest)


def instance_of(ctx: HandlerContext) -> WorkflowInstance:
    return ctx.instance


def _attachable_refinements(node: WorkflowNode) -> frozenset[str]:
    """The refinements an opcode may legitimately attach to its output. A WRITE
    boundary node may attach anything (it verified the effect). Others only the
    refinement their verification/preparation semantics produced."""
    if node.node_class == NodeClass.WRITE:
        from ..types.system import REFINEMENTS

        return REFINEMENTS
    per_opcode = {
        "RECONCILE": frozenset({"Admitted", "Verified", "Confirmed", "VerifiedEffect"}),
        "PREPARE_ACTION": frozenset({"Candidate"}),
        "VALIDATE_SCHEMA": frozenset({"Verified"}),
        "VERIFY_EXECUTION": frozenset({"Confirmed", "VerifiedEffect"}),
        "ASSERT_STATE": frozenset({"Verified"}),
        "READ_STATE": frozenset({"Verified"}),
        "FETCH": frozenset({"Admitted", "Verified"}),
        "EVALUATE_RULE": frozenset({"Candidate"}),
        "REQUEST_INPUT": frozenset({"Admitted"}),
        "REQUEST_APPROVAL": frozenset({"Admitted", "Authorized"}),
        "REQUEST_REVIEW": frozenset({"Admitted"}),
    }
    return per_opcode.get(node.opcode, frozenset())


def _unwrap(value: Any) -> Any:
    from .values import RuntimeValue

    return value.value if isinstance(value, RuntimeValue) else value


def _receipt(value: Any) -> str:
    if isinstance(value, dict):
        return value.get("receipt_ref") or value.get("receipt") or "runtime"
    return "runtime"


def _summarize(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _summarize(v) for k, v in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_summarize(v) for v in value]
    return value
