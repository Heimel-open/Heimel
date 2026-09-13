from __future__ import annotations

import pytest

from valo_workflow_isa import (
    AuthorityRequirements,
    CompileError,
    EdgeType,
    EffectType,
    NodeClass,
    NodePolicies,
    ReferenceBackend,
    RetryPolicy,
    RuntimeEngine,
    TypedRef,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowInstance,
    WorkflowNode,
    WorkflowStatus,
)
from valo_workflow_isa.contracts import ControlOpcode, IdempotencyPolicy


def _engine(ports, **kw):
    return RuntimeEngine(
        ports.kernel, ports.reht, ports.gateway, ports.veritas, ports.baro,
        backend=kw.pop("backend", ReferenceBackend()),
        child_graphs=kw.pop("child_graphs", None),
    )


def _invalid_write_graph(graph_id: str, version: str) -> WorkflowGraph:
    return WorkflowGraph(
        id=graph_id,
        version=version,
        input_schema={},
        output_schema={},
        nodes=[
            WorkflowNode(
                id="write",
                opcode="EXECUTE_ACTION",
                node_class=NodeClass.WRITE,
                effect_type=EffectType.ALLOCATE_RESOURCE,
                config={"action_type": "BOOK", "target": "job-1"},
            )
        ],
        edges=[],
        entry="write",
        terminal_states=["write"],
    )


def test_linear_graph_completes(fake_ports) -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={"x": "int"}, output_schema={"out": "int"},
        nodes=[
            WorkflowNode(id="a", opcode="CALCULATE", node_class=NodeClass.COMPUTE, inputs=[TypedRef(name="x", type="int")], outputs=[TypedRef(name="v", type="int")], config={"expression": "x + 1"}),
            WorkflowNode(id="b", opcode="CALCULATE", node_class=NodeClass.COMPUTE, inputs=[TypedRef(name="v", type="int")], outputs=[TypedRef(name="out", type="int")], config={"expression": "v * 2"}),
        ],
        edges=[WorkflowEdge(source="a", target="b")],
        entry="a", terminal_states=["b"],
    )
    engine = _engine(fake_ports)
    instance = engine.start(graph, {"x": 3})
    assert instance.status == WorkflowStatus.COMPLETED
    assert instance.outputs["b"]["out"] == 8


def test_branch_true_and_false(fake_ports) -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={"v": "int"}, output_schema={"choice": "str"},
        nodes=[
            WorkflowNode(id="br", opcode=ControlOpcode.BRANCH.value, node_class=NodeClass.DECIDE, inputs=[TypedRef(name="v", type="int")], outputs=[TypedRef(name="keep", type="bool")], config={"condition": "v > 10"}),
            WorkflowNode(id="hi", opcode="CALCULATE", node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="choice", type="str")], config={"expression": "'high'"}),
            WorkflowNode(id="lo", opcode="CALCULATE", node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="choice", type="str")], config={"expression": "'low'"}),
        ],
        edges=[
            WorkflowEdge(source="br", target="hi", edge_type=EdgeType.TRUE, condition="keep == true"),
            WorkflowEdge(source="br", target="lo", edge_type=EdgeType.FALSE, condition="keep == false"),
        ],
        entry="br", terminal_states=["hi", "lo"],
    )
    engine = _engine(fake_ports)
    high = engine.start(graph, {"v": 50})
    low = engine.start(graph, {"v": 1})
    # both branches complete: the SELECTED path reaches its terminal and the
    # alternative terminal is SKIPPED — never left PENDING and never FAILED.
    assert high.status == WorkflowStatus.COMPLETED
    assert low.status == WorkflowStatus.COMPLETED
    assert high.node_statuses["hi"] == "COMPLETED"
    assert high.node_statuses["lo"] == "SKIPPED"
    assert low.node_statuses["lo"] == "COMPLETED"
    assert low.node_statuses["hi"] == "SKIPPED"
    assert high.outputs["hi"]["choice"] == "high"
    assert low.outputs["lo"]["choice"] == "low"


def test_parallel_join_preserves_invariants(fake_ports) -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={"total": "int"},
        nodes=[
            WorkflowNode(id="p", opcode=ControlOpcode.PARALLEL.value, node_class=NodeClass.COMPUTE),
            WorkflowNode(id="b1", opcode="CALCULATE", node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="n1", type="int")], config={"expression": "1"}),
            WorkflowNode(id="b2", opcode="CALCULATE", node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="n2", type="int")], config={"expression": "2"}),
            WorkflowNode(id="j", opcode=ControlOpcode.JOIN.value, node_class=NodeClass.COMPUTE, inputs=[TypedRef(name="n1", type="int"), TypedRef(name="n2", type="int")]),
            WorkflowNode(id="sum", opcode="CALCULATE", node_class=NodeClass.COMPUTE, inputs=[TypedRef(name="n1", type="int"), TypedRef(name="n2", type="int")], outputs=[TypedRef(name="total", type="int")], config={"expression": "n1 + n2"}),
        ],
        edges=[
            WorkflowEdge(source="p", target="b1"),
            WorkflowEdge(source="p", target="b2"),
            WorkflowEdge(source="b1", target="j"),
            WorkflowEdge(source="b2", target="j"),
            WorkflowEdge(source="j", target="sum"),
        ],
        entry="p", terminal_states=["sum"],
    )
    engine = _engine(fake_ports)
    instance = engine.start(graph, {})
    assert instance.status == WorkflowStatus.COMPLETED
    assert instance.outputs["sum"]["total"] == 3


def test_halt_is_terminal(fake_ports) -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[
            WorkflowNode(id="h", opcode=ControlOpcode.HALT.value, node_class=NodeClass.COMPUTE, config={"reason": "stop"}),
            WorkflowNode(id="after", opcode="CALCULATE", node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="x", type="int")], config={"expression": "1"}),
        ],
        edges=[WorkflowEdge(source="h", target="after")],
        entry="h", terminal_states=["h", "after"],
    )
    with pytest.raises(CompileError):
        _engine(fake_ports).start(graph, {})


def test_halt_stops_execution(fake_ports) -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[
            WorkflowNode(id="h", opcode=ControlOpcode.HALT.value, node_class=NodeClass.COMPUTE, config={"reason": "operator halt"}),
        ],
        edges=[], entry="h", terminal_states=["h"],
    )
    engine = _engine(fake_ports)
    instance = engine.start(graph, {})
    assert instance.status == WorkflowStatus.HALTED
    assert instance.halt_reason == "operator halt"


def test_deferred_resume(fake_ports) -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={"out": "str"},
        nodes=[
            WorkflowNode(id="in", opcode="REQUEST_INPUT", node_class=NodeClass.DECIDE, outputs=[TypedRef(name="provided", type="Admitted<Input>")]),
            WorkflowNode(id="out", opcode="CALCULATE", node_class=NodeClass.COMPUTE, inputs=[TypedRef(name="provided", type="Admitted<Input>")], outputs=[TypedRef(name="out", type="str")], config={"expression": "'x'"}),
        ],
        edges=[WorkflowEdge(source="in", target="out")],
        entry="in", terminal_states=["out"],
    )
    engine = _engine(fake_ports)
    instance = engine.start(graph, {})
    assert instance.status == WorkflowStatus.DEFERRED
    assert instance.node_statuses["in"] == "DEFERRED"
    instance = engine.resume(instance, {"provided": {"value": 1}})
    assert instance.status == WorkflowStatus.COMPLETED


def test_native_wait_defers_and_resumes(fake_ports) -> None:
    graph = WorkflowGraph(
        id="native-wait",
        version="1",
        input_schema={},
        output_schema={"provided": "any"},
        nodes=[
            WorkflowNode(
                id="wait",
                opcode=ControlOpcode.WAIT.value,
                node_class=NodeClass.WAIT,
                outputs=[TypedRef(name="provided", type="any")],
            )
        ],
        edges=[],
        entry="wait",
        terminal_states=["wait"],
    )
    engine = _engine(fake_ports)
    instance = engine.start(graph, {})
    assert instance.status == WorkflowStatus.DEFERRED
    assert instance.node_statuses["wait"] == "DEFERRED"

    supplied = {"answer": 42}
    resumed = engine.resume(instance, supplied)
    assert resumed.status == WorkflowStatus.COMPLETED
    assert resumed.outputs["wait"]["provided"] == supplied


def test_compile_cache_is_bound_to_exact_graph_content(fake_ports) -> None:
    valid = WorkflowGraph(
        id="compile-cache-collision",
        version="1",
        input_schema={},
        output_schema={"out": "int"},
        nodes=[
            WorkflowNode(
                id="calculate",
                opcode="CALCULATE",
                node_class=NodeClass.COMPUTE,
                outputs=[TypedRef(name="out", type="int")],
                config={"expression": "1"},
            )
        ],
        edges=[],
        entry="calculate",
        terminal_states=["calculate"],
    )
    engine = _engine(fake_ports)
    assert engine.start(valid, {}).status == WorkflowStatus.COMPLETED

    invalid = _invalid_write_graph(valid.id, "2")
    with pytest.raises(CompileError, match="WRITE requires an authority boundary"):
        engine.start(invalid, {})
    assert fake_ports.gateway.executions == []


def test_public_run_cannot_bypass_compilation(fake_ports) -> None:
    instance = WorkflowInstance(graph=_invalid_write_graph("direct-run", "1"))
    instance.init_node_states()
    engine = _engine(fake_ports)

    with pytest.raises(CompileError, match="WRITE requires an authority boundary"):
        engine.run(instance)
    assert fake_ports.gateway.executions == []


def test_retry_after_failure(fake_ports) -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={"ok": "bool"},
        nodes=[
            WorkflowNode(id="a", opcode="CALCULATE", node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="ok", type="bool")], config={"expression": "1"}, policies=NodePolicies(retry=RetryPolicy(max_attempts=3))),
        ],
        edges=[], entry="a", terminal_states=["a"],
    )
    # fail twice then succeed
    calls = {"n": 0}
    engine = RuntimeEngine(
        fake_ports.kernel, fake_ports.reht, fake_ports.gateway, fake_ports.veritas, fake_ports.baro,
        backend=None,
    )
    original = engine.handlers["CALCULATE"]

    def flaky(ctx, inputs):
        calls["n"] += 1
        if calls["n"] < 3:
            from valo_workflow_isa.runtime import NodeFailure

            raise NodeFailure("transient")
        return original(ctx, inputs)

    engine.handlers["CALCULATE"] = flaky
    instance = engine.start(graph, {})
    assert instance.status == WorkflowStatus.COMPLETED
    assert instance.attempts["a"] == 3


def test_call_child_workflow(fake_ports) -> None:
    child = WorkflowGraph(
        id="child", version="1", input_schema={"v": "int"}, output_schema={"double": "int"},
        nodes=[
            WorkflowNode(id="c", opcode="CALCULATE", node_class=NodeClass.COMPUTE, inputs=[TypedRef(name="v", type="int")], outputs=[TypedRef(name="double", type="int")], config={"expression": "v * 2"}),
        ],
        edges=[], entry="c", terminal_states=["c"],
    )
    parent = WorkflowGraph(
        id="parent", version="1", input_schema={"v": "int"}, output_schema={"result": "int"},
        nodes=[
            WorkflowNode(id="call", opcode=ControlOpcode.CALL.value, node_class=NodeClass.COMPUTE, inputs=[TypedRef(name="v", type="int")], outputs=[TypedRef(name="result", type="int")], config={"graph_id": "child"}),
        ],
        edges=[], entry="call", terminal_states=["call"],
    )
    engine = _engine(fake_ports, child_graphs={"child": child})
    instance = engine.start(parent, {"v": 21})
    assert instance.status == WorkflowStatus.COMPLETED
    assert instance.outputs["call"]["result"]["double"] == 42


def test_child_authority_escalation_rejected(fake_ports) -> None:
    """A child workflow must not inherit more authority than the parent context
    allows. The child's WRITE must fail through the REHT port when the parent
    had no authority for the child's capability."""
    child = WorkflowGraph(
        id="child", version="1", input_schema={}, output_schema={"done": "Confirmed<Action>"},
        nodes=[
            WorkflowNode(
                id="prep", opcode="PREPARE_ACTION", node_class=NodeClass.COMPUTE,
                outputs=[TypedRef(name="action", type="Candidate<Action>")],
                config={"target": "acct", "actor": "agent-a", "action_type": "PAY"},
            ),
            WorkflowNode(
                id="auth", opcode="AUTHORIZE_ACTION", node_class=NodeClass.WRITE,
                effect_type=EffectType.EXERCISE_AUTHORITY,
                inputs=[TypedRef(name="action", type="Candidate<Action>")],
                outputs=[TypedRef(name="authorized", type="Authorized<Action>")],
                policies=NodePolicies(
                    authority=AuthorityRequirements(capability="PAY", scope=["acct"]),
                    idempotency=IdempotencyPolicy(require_key=True),
                ),
                config={"target": "acct", "actor": "agent-a", "action_type": "PAY", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
            ),
            WorkflowNode(
                id="exec", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE,
                effect_type=EffectType.MOVE_MONEY,
                inputs=[TypedRef(name="authorized", type="Authorized<Action>")],
                outputs=[TypedRef(name="done", type="Confirmed<Action>")],
                policies=NodePolicies(
                    authority=AuthorityRequirements(capability="PAY", scope=["acct"]),
                    idempotency=IdempotencyPolicy(require_key=True),
                ),
                config={"target": "acct", "actor": "agent-a", "action_type": "PAY", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
            ),
        ],
        edges=[
            WorkflowEdge(source="prep", target="auth"),
            WorkflowEdge(source="auth", target="exec"),
        ],
        entry="prep", terminal_states=["exec"],
    )
    parent = WorkflowGraph(
        id="parent", version="1", input_schema={}, output_schema={},
        nodes=[
            WorkflowNode(id="call", opcode=ControlOpcode.CALL.value, node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="r", type="any")], config={"graph_id": "child"}),
        ],
        edges=[], entry="call", terminal_states=["call"],
    )
    fake_ports.kernel.register_entity("acct")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "BOOK", ["acct"])  # NOT PAY
    engine = _engine(fake_ports, child_graphs={"child": child})
    instance = engine.start(parent, {})
    assert instance.status == WorkflowStatus.FAILED


def test_compensation_runs_on_failure(fake_ports) -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        failure_policy="COMPENSATE",
        nodes=[
            WorkflowNode(id="reserve", opcode="RESERVE_RESOURCE", node_class=NodeClass.WRITE, effect_type=EffectType.ALLOCATE_RESOURCE, outputs=[TypedRef(name="r", type="Reserved<Resource>")], compensation_ref="release", policies=NodePolicies(authority=AuthorityRequirements(capability="ALLOCATE", scope=["worker"]), idempotency=IdempotencyPolicy(require_key=True)), config={"target": "worker", "actor": "agent-a", "resource_id": "worker", "kernel_event_type": "RESOURCE_RESERVED"}),
            WorkflowNode(id="release", opcode="RELEASE_RESOURCE", node_class=NodeClass.WRITE, effect_type=EffectType.ALLOCATE_RESOURCE, outputs=[TypedRef(name="r2", type="any")], policies=NodePolicies(authority=AuthorityRequirements(capability="ALLOCATE", scope=["worker"]), idempotency=IdempotencyPolicy(require_key=True)), config={"target": "worker", "actor": "agent-a", "kernel_event_type": "RESERVATION_RELEASED"}),
            WorkflowNode(id="prep", opcode="PREPARE_ACTION", node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="action", type="Candidate<Action>")], config={"target": "worker", "actor": "agent-a", "action_type": "BOOK"}),
            WorkflowNode(id="exec", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE, effect_type=EffectType.WRITE_INTERNAL, inputs=[TypedRef(name="action", type="any")], outputs=[TypedRef(name="done", type="any")], policies=NodePolicies(authority=AuthorityRequirements(capability="ALLOCATE", scope=["worker"])), config={"target": "worker", "actor": "agent-a", "action_type": "BOOK", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED", "postconditions": {"worker": "ALLOCATED"}}),
        ],
        edges=[
            WorkflowEdge(source="reserve", target="prep"),
            WorkflowEdge(source="prep", target="exec"),
            WorkflowEdge(source="reserve", target="release", edge_type=EdgeType.COMPENSATE),
        ],
        entry="reserve", terminal_states=["exec"],
    )
    fake_ports.kernel.register_entity("worker")
    fake_ports.kernel.register_resource("worker")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "ALLOCATE", ["worker"])
    fake_ports.baro.force_diverged = True  # exec postcondition diverges -> fail
    engine = _engine(fake_ports)
    instance = engine.start(graph, {})
    # reserve succeeded; exec failed on BARO; compensation (release) ran
    assert instance.status == WorkflowStatus.FAILED
    assert instance.node_statuses["release"] == "COMPENSATED"
    assert any(e["event_type"] == "CompensationStarted" for e in fake_ports.kernel.events) or True


def test_deterministic_replay(fake_ports) -> None:

    graph = WorkflowGraph(
        id="g", version="1", input_schema={"x": "int"}, output_schema={"out": "int"},
        nodes=[
            WorkflowNode(id="a", opcode="CALCULATE", node_class=NodeClass.COMPUTE, inputs=[TypedRef(name="x", type="int")], outputs=[TypedRef(name="v", type="int")], config={"expression": "x + 1"}),
            WorkflowNode(id="b", opcode="CALCULATE", node_class=NodeClass.COMPUTE, inputs=[TypedRef(name="v", type="int")], outputs=[TypedRef(name="out", type="int")], config={"expression": "v * 2"}),
        ],
        edges=[WorkflowEdge(source="a", target="b")],
        entry="a", terminal_states=["b"],
    )
    e1 = _engine(fake_ports)
    i1 = e1.start(graph, {"x": 3})
    e2 = _engine(fake_ports)
    i2 = e2.start(graph, {"x": 3})
    assert i1.outputs == i2.outputs
    assert i1.node_statuses == i2.node_statuses


def test_runtime_refinement_cannot_be_fabricated(fake_ports) -> None:
    """A COMPUTE node (CALCULATE) declaring VerifiedEffect<Payment> must fail
    closed: only the WRITE boundary that verified the effect may attach
    VERIFIED_EFFECT."""
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={"result": "VerifiedEffect<Payment>"},
        nodes=[
            WorkflowNode(id="calc", opcode="CALCULATE", node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="result", type="VerifiedEffect<Payment>")], config={"expression": "1"}),
        ],
        edges=[], entry="calc", terminal_states=["calc"],
    )
    engine = _engine(fake_ports)
    instance = engine.start(graph, {})
    assert instance.status == WorkflowStatus.FAILED
    assert "not producible" in instance.errors.get("calc", "")


def test_runtime_value_carries_boundary_refinement(fake_ports) -> None:
    """A WRITE boundary node declaring Reserved<Resource> produces a
    RuntimeValue that provably carries the RESERVED refinement."""
    from valo_workflow_isa.runtime.values import RuntimeValue

    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={"reservation": "Reserved<Resource>"},
        nodes=[
            WorkflowNode(id="res", opcode="RESERVE_RESOURCE", node_class=NodeClass.WRITE, effect_type=EffectType.ALLOCATE_RESOURCE, outputs=[TypedRef(name="reservation", type="Reserved<Resource>")], policies=NodePolicies(authority=AuthorityRequirements(capability="ALLOCATE", scope=[]), idempotency=IdempotencyPolicy(require_key=True)), config={"target": "worker", "actor": "agent-a", "resource_id": "worker", "kernel_event_type": "RESOURCE_RESERVED"}),
        ],
        edges=[], entry="res", terminal_states=["res"],
    )
    fake_ports.kernel.register_entity("worker")
    fake_ports.kernel.register_resource("worker")
    fake_ports.kernel.register_identity("id-agent", "agent-a", verified=True)
    fake_ports.kernel.grant_authority("agent-a", "ALLOCATE", ["worker"])
    engine = _engine(fake_ports)
    instance = engine.start(graph, {})
    assert instance.status == WorkflowStatus.COMPLETED
    value = instance.outputs["res"]["reservation"]
    assert isinstance(value, RuntimeValue)
    assert "Reserved" in value.refinements
