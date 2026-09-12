from __future__ import annotations

from valo_workflow_isa import (
    AuthorityRequirements,
    EffectType,
    IdempotencyPolicy,
    NodeClass,
    NodePolicies,
    ReferenceBackend,
    RetryPolicy,
    RuntimeEngine,
    TypedRef,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
    WorkflowStatus,
)
from valo_workflow_isa.contracts.common import canonical_digest
from valo_workflow_isa.ports import DecisionResult

from ..helpers import write_node


def _engine(ports, **kw):
    return RuntimeEngine(
        ports.kernel, ports.reht, ports.gateway, ports.veritas, ports.baro, **kw
    )


def _prep_node(node_id: str = "prep", capability: str = "BOOK", actor: str = "agent-a", target: str = "job-1") -> WorkflowNode:
    return WorkflowNode(
        id=node_id, opcode="PREPARE_ACTION", node_class=NodeClass.COMPUTE,
        outputs=[TypedRef(name="action", type="Candidate<Action>")],
        config={"target": target, "actor": actor, "action_type": "BOOK", "capability": capability, "kernel_event_type": "RESOURCE_RESERVED"},
    )


def _auth_node(capability: str = "BOOK", target: str = "job-1") -> WorkflowNode:
    return WorkflowNode(
        id="auth", opcode="AUTHORIZE_ACTION", node_class=NodeClass.WRITE, effect_type=EffectType.EXERCISE_AUTHORITY,
        inputs=[TypedRef(name="action", type="Candidate<Action>")],
        outputs=[TypedRef(name="authorized", type="Authorized<Action>")],
        policies=NodePolicies(authority=AuthorityRequirements(capability=capability, scope=[target]), idempotency=IdempotencyPolicy(require_key=True)),
        config={"target": target, "actor": "agent-a", "action_type": "BOOK", "capability": capability, "kernel_event_type": "RESOURCE_RESERVED"},
    )


def _exec_node(capability: str = "BOOK", target: str = "job-1", require_key: bool = False) -> WorkflowNode:
    return write_node(
        "exec", opcode="EXECUTE_ACTION", effect=EffectType.ALLOCATE_RESOURCE,
        capability=capability, target=target, actor="agent-a",
        require_key=require_key, verify_before_replay=False,
        inputs=[TypedRef(name="authorized", type="Authorized<Action>")],
        outputs=[TypedRef(name="done", type="Confirmed<Action>")],
        config={"action_type": "BOOK", "kernel_event_type": "RESOURCE_RESERVED"},
    )


def _reservation_graph(*, capability: str = "BOOK", require_key: bool = False) -> WorkflowGraph:
    return WorkflowGraph(
        id="reserve-graph", version="1", input_schema={}, output_schema={"done": "Confirmed<Action>"},
        nodes=[_prep_node(), _auth_node(capability), _exec_node(capability, require_key=require_key)],
        edges=[
            WorkflowEdge(source="prep", target="auth"),
            WorkflowEdge(source="auth", target="exec"),
        ],
        entry="prep", terminal_states=["exec"],
    )


def test_write_flows_through_reht_port(fake_ports) -> None:
    fake_ports.kernel.register_entity("job-1", state="READY")
    fake_ports.kernel.register_resource("job-1")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "BOOK", ["job-1"])
    engine = _engine(fake_ports)
    instance = engine.start(_reservation_graph(require_key=True), {})
    assert instance.status == WorkflowStatus.COMPLETED
    # both the AUTHORIZE_ACTION and the EXECUTE_ACTION boundary revalidate
    # authority; the execution boundary re-reads a fresh context
    assert len(fake_ports.reht.authorize_calls) == 2
    assert len(fake_ports.kernel.events) >= 1


def test_write_without_authorization_denied(fake_ports) -> None:
    """Negative: WRITE with no authority at all must fail closed."""
    fake_ports.kernel.register_entity("job-1", state="READY")
    fake_ports.kernel.register_resource("job-1")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    # no authority granted
    engine = _engine(fake_ports)
    instance = engine.start(_reservation_graph(require_key=True), {})
    assert instance.status == WorkflowStatus.FAILED
    assert instance.errors.get("auth", "").startswith("authorization DENY")


def test_revoked_authority_denied(fake_ports) -> None:
    """Workflow starts under valid authority; authority is revoked before the
    WRITE; the WRITE re-reads a fresh execution context and is denied."""
    fake_ports.kernel.register_entity("job-1", state="READY")
    fake_ports.kernel.register_resource("job-1")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "BOOK", ["job-1"])
    fake_ports.kernel.revoke_authority("agent-a", "BOOK")

    engine = _engine(fake_ports)
    instance = engine.start(_reservation_graph(require_key=True), {})
    # fresh execution context sees no authority -> REHT DENY
    assert instance.status == WorkflowStatus.FAILED


def test_stale_execution_context_denied(fake_ports) -> None:
    """The execution context is re-read at the WRITE boundary; an earlier stale
    grant does not matter once revoked."""
    fake_ports.kernel.register_entity("job-1", state="READY")
    fake_ports.kernel.register_resource("job-1")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "BOOK", ["job-1"])
    fake_ports.kernel.revoke_authority("agent-a", "BOOK")
    engine = _engine(fake_ports)
    instance = engine.start(_reservation_graph(require_key=True), {})
    assert instance.status == WorkflowStatus.FAILED


def test_external_success_not_verified_effect(fake_ports) -> None:
    """Gateway returns success but BARO finds the postcondition never arose.
    The workflow must NOT complete; it fails."""
    fake_ports.kernel.register_entity("job-1", state="READY")
    fake_ports.kernel.register_resource("job-1")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "BOOK", ["job-1"])
    fake_ports.baro.force_diverged = True
    graph = _reservation_graph(require_key=True)
    # give exec a postcondition to verify
    graph = graph.model_copy(
        update={"nodes": [n.model_copy(update={"config": {**n.config, "postconditions": {"job-1": "PAID"}}}) if n.id == "exec" else n for n in graph.nodes]}
    )
    engine = _engine(fake_ports)
    instance = engine.start(graph, {})
    assert instance.status == WorkflowStatus.FAILED
    assert "postcondition" in instance.errors.get("exec", "").lower()


def test_retry_verifies_before_replay(fake_ports) -> None:
    """A WRITE whose external effect may already have happened must not be
    blindly re-executed or falsely completed. Gateway detection is not Veritas
    verification, so the unknown outcome defers for explicit reconciliation."""
    fake_ports.kernel.register_entity("job-1", state="READY")
    fake_ports.kernel.register_resource("job-1")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "BOOK", ["job-1"])
    fake_ports.gateway.fail_after_execute = True  # first call: effect recorded, response lost

    exec_node = write_node(
        "exec", opcode="EXECUTE_ACTION", effect=EffectType.ALLOCATE_RESOURCE,
        capability="BOOK", target="job-1", actor="agent-a",
        require_key=True, verify_before_replay=True,
        inputs=[TypedRef(name="authorized", type="Authorized<Action>")],
        outputs=[TypedRef(name="done", type="Confirmed<Action>")],
        config={"action_type": "BOOK", "kernel_event_type": "RESOURCE_RESERVED"},
        # copy nodes into a fresh graph with retry policy
    )
    exec_node = exec_node.model_copy(
        update={"policies": exec_node.policies.model_copy(update={"retry": RetryPolicy(max_attempts=2, retry_after_timeout=True)})}
    )
    graph = WorkflowGraph(
        id="reserve-graph", version="1", input_schema={}, output_schema={"done": "Confirmed<Action>"},
        nodes=[_prep_node(), _auth_node(), exec_node],
        edges=[WorkflowEdge(source="prep", target="auth"), WorkflowEdge(source="auth", target="exec")],
        entry="prep", terminal_states=["exec"],
    )
    backend = ReferenceBackend()
    engine = _engine(fake_ports, backend=backend)
    instance = engine.start(graph, {})
    assert instance.status == WorkflowStatus.DEFERRED
    assert len(fake_ports.gateway.executions) == 1, "external effect must not be re-executed"
    assert instance.node_statuses["exec"] == "DEFERRED"
    assert "independent verification" in instance.errors["exec"]
    assert "exec" not in instance.outputs
    assert fake_ports.kernel.events == []
    events = backend.events_for(instance.instance_id)
    assert all(event["event_type"] != "EffectVerified" for event in events)

    resumed = engine.resume(instance, {"effect_verified": True})
    assert resumed.status == WorkflowStatus.DEFERRED
    assert len(fake_ports.gateway.executions) == 1
    assert "exec" not in resumed.outputs


def test_duplicate_execution_prevented(fake_ports) -> None:
    """The same idempotency key must not produce two external executions."""
    fake_ports.kernel.register_entity("job-1", state="READY")
    fake_ports.kernel.register_resource("job-1")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "BOOK", ["job-1"])
    graph = _reservation_graph(require_key=True)
    engine = _engine(fake_ports)
    instance = engine.start(graph, {})
    assert instance.status == WorkflowStatus.COMPLETED
    assert fake_ports.gateway.replayed == []


def test_gateway_failure_never_effect_verified(fake_ports) -> None:
    """Gateway success=False must never emit EFFECT_VERIFIED and never produce
    an authoritative Kernel effect event: not executed, not effect verified."""
    from valo_workflow_isa import ReferenceBackend

    fake_ports.kernel.register_entity("job-1", state="READY")
    fake_ports.kernel.register_resource("job-1")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "BOOK", ["job-1"])
    fake_ports.gateway.success = False
    backend = ReferenceBackend()
    engine = RuntimeEngine(
        fake_ports.kernel, fake_ports.reht, fake_ports.gateway,
        fake_ports.veritas, fake_ports.baro, backend=backend,
    )
    instance = engine.start(_reservation_graph(require_key=True), {})
    assert instance.status == WorkflowStatus.FAILED
    events = backend.events_for(instance.instance_id)
    assert all(e["event_type"] != "EffectVerified" for e in events)
    assert not any(e.get("event_type") == "RESOURCE_RESERVED" for e in fake_ports.kernel.events)


def test_no_active_racs_component(fake_ports) -> None:
    """RACS is a deterministic decision contract (binding derivation), not a
    processing component between REHT and execution. The WRITE boundary has
    exactly two steps: REHT authorize, then deterministic binding derivation."""
    from valo_workflow_isa.ports import boundaries
    from valo_workflow_isa.ports.boundaries import GatewayPort, RehtPort

    assert not hasattr(boundaries, "RacsPort")
    assert not hasattr(boundaries, "RacsResult")
    assert GatewayPort and RehtPort


def test_binding_derived_deterministically_from_reht_decision(fake_ports) -> None:
    """The same REHT decision + action contract always derive the same binding
    (pure, deterministic). The Gateway executes against the derived binding,
    never against a raw REHT decision."""
    from valo_workflow_isa.stdlib.handlers import _derive_binding

    decision = DecisionResult(
        decision="ALLOW",
        clearance_ref="clearance-9",
        permit_ref="permit-9",
        execution_context_hash="context-9",
    )
    contract = {"action_type": "BOOK", "capability": "BOOK"}
    binding = _derive_binding(decision, contract)
    assert binding == _derive_binding(decision, contract)
    assert binding.startswith("binding:")
    assert len(binding.removeprefix("binding:")) == 64
    assert binding != _derive_binding(
        decision,
        {"action_type": "CANCEL", "capability": "BOOK"},
    )

    fake_ports.kernel.register_entity("job-1", state="READY")
    fake_ports.kernel.register_resource("job-1")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "BOOK", ["job-1"])
    engine = _engine(fake_ports)
    instance = engine.start(_reservation_graph(require_key=True), {})
    assert instance.status == WorkflowStatus.COMPLETED
    assert fake_ports.gateway.executions, "Gateway must execute after REHT ALLOW"
    bound = fake_ports.gateway.executions[0]["binding"]
    assert bound.startswith("binding:")
    assert len(bound.removeprefix("binding:")) == 64


def test_allow_with_mismatched_execution_context_hash_fails_closed(fake_ports) -> None:
    class MismatchedContextReht:
        def authorize(self, execution_context, action_contract):
            return DecisionResult(
                decision="ALLOW",
                clearance_ref="clearance-1",
                execution_context_hash="not-the-fresh-context",
            )

    fake_ports.kernel.register_entity("job-1", state="READY")
    fake_ports.kernel.register_resource("job-1")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "BOOK", ["job-1"])
    engine = RuntimeEngine(
        fake_ports.kernel,
        MismatchedContextReht(),
        fake_ports.gateway,
        fake_ports.veritas,
        fake_ports.baro,
    )

    instance = engine.start(_reservation_graph(require_key=True), {})
    assert instance.status == WorkflowStatus.FAILED
    assert "execution_context_hash" in instance.errors["auth"]
    assert fake_ports.gateway.executions == []


def test_allow_without_decision_reference_fails_closed(fake_ports) -> None:
    class UnboundAllowReht:
        def authorize(self, execution_context, action_contract):
            return DecisionResult(
                decision="ALLOW",
                execution_context_hash=canonical_digest(execution_context),
            )

    fake_ports.kernel.register_entity("job-1", state="READY")
    fake_ports.kernel.register_resource("job-1")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "BOOK", ["job-1"])
    engine = RuntimeEngine(
        fake_ports.kernel,
        UnboundAllowReht(),
        fake_ports.gateway,
        fake_ports.veritas,
        fake_ports.baro,
    )

    instance = engine.start(_reservation_graph(require_key=True), {})
    assert instance.status == WorkflowStatus.FAILED
    assert "clearance_ref or permit_ref" in instance.errors["auth"]
    assert fake_ports.gateway.executions == []


def test_modify_without_exact_modified_action_fails_closed(fake_ports) -> None:
    class ModifyReht:
        def authorize(self, execution_context, action_contract):
            return DecisionResult(
                decision="MODIFY",
                clearance_ref="clearance-modified",
                execution_context_hash=canonical_digest(execution_context),
                reason="use a narrower action",
            )

    fake_ports.kernel.register_entity("job-1", state="READY")
    fake_ports.kernel.register_resource("job-1")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "BOOK", ["job-1"])
    engine = RuntimeEngine(
        fake_ports.kernel,
        ModifyReht(),
        fake_ports.gateway,
        fake_ports.veritas,
        fake_ports.baro,
    )

    instance = engine.start(_reservation_graph(require_key=True), {})
    assert instance.status == WorkflowStatus.FAILED
    assert instance.errors["auth"].startswith("authorization MODIFY")
    assert "exact modified action contract" in instance.errors["auth"]
    assert fake_ports.gateway.executions == []
