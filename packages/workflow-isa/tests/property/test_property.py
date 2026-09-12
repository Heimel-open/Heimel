from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st

from valo_workflow_isa import (
    CompileError,
    NodeClass,
    RuntimeEngine,
    TypedRef,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
    WorkflowStatus,
    compile_graph,
)
from valo_workflow_isa.types import REFINEMENTS, WRAPPER_LEVELS, can_consume

WRAPPERS = list(WRAPPER_LEVELS)
BASES = st.text(min_size=1, max_size=6).map(lambda s: "".join(ch for ch in s if ch.isalnum()) or "T").filter(lambda b: b != "any")


@settings(max_examples=60)
@given(st.sampled_from(list(REFINEMENTS)), st.sampled_from(list(REFINEMENTS)))
def test_property_no_cross_refinement_promotion(a, b) -> None:
    """Different refinements of the same base never promote to each other in
    either direction (orthogonality across the full runtime refinement set)."""
    if a == b:
        assert can_consume(f"{a}<T>", f"{b}<T>")
        return
    assert not can_consume(f"{a}<T>", f"{b}<T>"), f"{a}<T> promoted to {b}<T>"
    assert not can_consume(f"{b}<T>", f"{a}<T>"), f"{b}<T> promoted to {a}<T>"


@settings(max_examples=30)
@given(st.sampled_from(["Executed", "VerifiedEffect", "Asserted", "Inferred"]))
def test_property_ff_only_refinements_stay_orthogonal(refinement) -> None:
    """Executed is not VerifiedEffect; Asserted/Inferred never satisfy
    Confirmed/Verified and vice versa."""
    counterpart = {
        "Executed": "VerifiedEffect",
        "VerifiedEffect": "Executed",
        "Asserted": "Verified",
        "Inferred": "Confirmed",
    }[refinement]
    assert not can_consume(f"{refinement}<X>", f"{counterpart}<X>")
    assert not can_consume(f"{counterpart}<X>", f"{refinement}<X>")


@settings(max_examples=40)
@given(st.lists(st.tuples(BASES, st.sampled_from(WRAPPERS + [None])), min_size=1, max_size=8))
def test_property_wrapper_consumption_is_transitive(pairs) -> None:
    """If A satisfies B and B satisfies C (same base), then A satisfies C."""
    types = [f"{w}<{b}>" if w else b for b, w in pairs]
    for a in types:
        for b in types:
            for c in types:
                if can_consume(a, b) and can_consume(b, c):
                    assert can_consume(a, c), f"transitivity broken: {a} >= {b} >= {c}"


@settings(max_examples=30)
@given(st.integers(min_value=1, max_value=5))
def test_property_typed_output_cannot_be_upgraded(n) -> None:
    """Refinements are orthogonal: no implicit promotion in either direction.
    `Verified<Recipient>` does not satisfy `Candidate<Recipient>` and
    `Candidate<Recipient>` never satisfies `Verified<Recipient>`."""
    verified = "Verified<Recipient>"
    candidate = "Candidate<Recipient>"
    admitted = "Admitted<Recipient>"
    assert not can_consume(candidate, verified)
    assert not can_consume(verified, candidate)
    assert not can_consume(admitted, verified)
    assert not can_consume(verified, admitted)
    assert 1 <= n <= 5


@settings(max_examples=25)
@given(
    st.lists(st.sampled_from(["CALCULATE", "COMPARE", "VALIDATE_SCHEMA"]), min_size=1, max_size=6),
)
def test_property_linear_graph_replays_deterministically(opcodes) -> None:
    from tests.conftest import (
        DictKernel,
        FakeBaro,
        FakeGateway,
        FakePorts,
        FakeReht,
        FakeVeritas,
    )

    nodes = [
        WorkflowNode(id=f"n{i}", opcode=op, node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="v", type="int")], config={"expression": "1"})
        for i, op in enumerate(opcodes)
    ]
    edges = [WorkflowEdge(source=nodes[i].id, target=nodes[i + 1].id) for i in range(len(nodes) - 1)]
    graph = WorkflowGraph(id="g", version="1", input_schema={}, output_schema={}, nodes=nodes, edges=edges, entry=nodes[0].id, terminal_states=[nodes[-1].id])
    compile_graph(graph)

    ports = FakePorts(DictKernel(), FakeReht(), FakeGateway(), FakeVeritas(), FakeBaro())
    e1 = RuntimeEngine(ports.kernel, ports.reht, ports.gateway, ports.veritas, ports.baro)
    e2 = RuntimeEngine(ports.kernel, ports.reht, ports.gateway, ports.veritas, ports.baro)
    i1 = e1.start(graph, {})
    i2 = e2.start(graph, {})
    assert i1.status == WorkflowStatus.COMPLETED
    assert i1.outputs == i2.outputs


def test_property_compiler_rejects_probabilistic_write_path() -> None:
    from valo_workflow_isa import (
        AuthorityRequirements,
        Determinism,
        EffectType,
        IdempotencyPolicy,
        NodePolicies,
    )

    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[
            WorkflowNode(id="p", opcode="EVALUATE_RULE", node_class=NodeClass.DECIDE, determinism=Determinism.PROBABILISTIC, outputs=[TypedRef(name="r", type="Candidate<Recipient>")], config={"model": "m", "model_version": "1", "confidence": 0.5, "source_context": "x"}),
            WorkflowNode(id="w", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE, effect_type=EffectType.MOVE_MONEY, inputs=[TypedRef(name="r", type="Confirmed<Recipient>")], outputs=[TypedRef(name="done", type="any")], policies=NodePolicies(authority=AuthorityRequirements(capability="PAY", scope=["a"]), idempotency=IdempotencyPolicy(require_key=True))),
        ],
        edges=[WorkflowEdge(source="p", target="w")],
        entry="p", terminal_states=["w"],
    )
    try:
        compile_graph(graph)
        raise AssertionError("compiler must reject probabilistic -> WRITE")
    except CompileError:
        pass


def test_property_halt_is_terminal() -> None:
    from valo_workflow_isa import ControlOpcode

    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[WorkflowNode(id="h", opcode=ControlOpcode.HALT.value, node_class=NodeClass.COMPUTE, config={"reason": "x"})],
        edges=[], entry="h", terminal_states=["h"],
    )
    from tests.conftest import (
        DictKernel,
        FakeBaro,
        FakeGateway,
        FakePorts,
        FakeReht,
        FakeVeritas,
    )

    ports = FakePorts(DictKernel(), FakeReht(), FakeGateway(), FakeVeritas(), FakeBaro())
    engine = RuntimeEngine(ports.kernel, ports.reht, ports.gateway, ports.veritas, ports.baro)
    instance = engine.start(graph, {})
    assert instance.status == WorkflowStatus.HALTED


def test_property_parallel_order_independence() -> None:
    """Scheduling order of independent parallel branches never changes the
    result."""
    from tests.conftest import (
        DictKernel,
        FakeBaro,
        FakeGateway,
        FakePorts,
        FakeReht,
        FakeVeritas,
    )

    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={"sum": "int"},
        nodes=[
            WorkflowNode(id="p", opcode="PARALLEL", node_class=NodeClass.COMPUTE),
            WorkflowNode(id="a", opcode="CALCULATE", node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="a", type="int")], config={"expression": "1"}),
            WorkflowNode(id="b", opcode="CALCULATE", node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="b", type="int")], config={"expression": "2"}),
            WorkflowNode(id="sum", opcode="CALCULATE", node_class=NodeClass.COMPUTE, inputs=[TypedRef(name="a", type="int"), TypedRef(name="b", type="int")], outputs=[TypedRef(name="sum", type="int")], config={"expression": "a + b"}),
        ],
        edges=[
            WorkflowEdge(source="p", target="a"),
            WorkflowEdge(source="p", target="b"),
            WorkflowEdge(source="a", target="sum"),
            WorkflowEdge(source="b", target="sum"),
        ],
        entry="p", terminal_states=["sum"],
    )
    results = set()
    for _ in range(5):
        ports = FakePorts(DictKernel(), FakeReht(), FakeGateway(), FakeVeritas(), FakeBaro())
        engine = RuntimeEngine(ports.kernel, ports.reht, ports.gateway, ports.veritas, ports.baro)
        instance = engine.start(graph, {})
        results.add(instance.outputs["sum"]["sum"])
    assert results == {3}
