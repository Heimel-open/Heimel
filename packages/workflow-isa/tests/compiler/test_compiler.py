from __future__ import annotations

import pytest

from valo_workflow_isa import CompileError, compile_graph
from valo_workflow_isa.contracts import (
    Determinism,
    EdgeType,
    EffectType,
    NodeClass,
    TypedRef,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)


def node(node_id: str, node_class=NodeClass.COMPUTE, opcode="CALCULATE", inputs=None, outputs=None, **kw) -> WorkflowNode:
    return WorkflowNode(id=node_id, opcode=opcode, node_class=node_class, inputs=inputs or [], outputs=outputs or [], **kw)


def test_valid_graph_compiles() -> None:
    graph = WorkflowGraph(
        id="g",
        version="1",
        input_schema={"in": "int"},
        output_schema={"out": "int"},
        nodes=[
            node("a", NodeClass.READ, "READ_STATE", outputs=[TypedRef(name="state", type="Verified<Job>")], config={"target": "j"}),
            node("b", NodeClass.COMPUTE, "CALCULATE", inputs=[TypedRef(name="state", type="Verified<Job>")], outputs=[TypedRef(name="out", type="int")], config={"expression": "1"}),
        ],
        edges=[WorkflowEdge(source="a", target="b")],
        entry="a",
        terminal_states=["b"],
    )
    compile_graph(graph)  # no raise


def test_unreachable_node_rejected() -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[node("a"), node("b"), node("c")],
        edges=[WorkflowEdge(source="a", target="b")],
        entry="a", terminal_states=["b"],
    )
    with pytest.raises(CompileError, match="unreachable"):
        compile_graph(graph)


def test_missing_producer_rejected() -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[node("b", inputs=[TypedRef(name="needed", type="int")])],
        edges=[], entry="b", terminal_states=["b"],
    )
    with pytest.raises(CompileError, match="has no producer"):
        compile_graph(graph)


def test_type_mismatch_rejected() -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[
            node("a", outputs=[TypedRef(name="recipient", type="Candidate<Recipient>")]),
            node("b", inputs=[TypedRef(name="recipient", type="Verified<Recipient>")]),
        ],
        edges=[WorkflowEdge(source="a", target="b")],
        entry="a", terminal_states=["b"],
    )
    with pytest.raises(CompileError):
        compile_graph(graph)


def test_graph_input_type_mismatch_rejected() -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={"recipient": "Candidate<Recipient>"}, output_schema={},
        nodes=[node("b", inputs=[TypedRef(name="recipient", type="Verified<Recipient>")])],
        edges=[], entry="b", terminal_states=["b"],
    )
    with pytest.raises(CompileError, match="cannot satisfy"):
        compile_graph(graph)


def test_no_cross_wrapper_promotion_in_graph() -> None:
    """Authorized<Document> must never satisfy a Verified<Document> requirement;
    refinements are orthogonal, not a strength ladder."""
    for produced, required in [
        ("Authorized<Document>", "Verified<Document>"),
        ("Reserved<Resource>", "Verified<Resource>"),
        ("Confirmed<Action>", "Authorized<Action>"),
        ("Verified<Document>", "Admitted<Document>"),
    ]:
        graph = WorkflowGraph(
            id="g", version="1", input_schema={}, output_schema={},
            nodes=[
                node("a", outputs=[TypedRef(name="v", type=produced)]),
                node("b", inputs=[TypedRef(name="v", type=required)]),
            ],
            edges=[WorkflowEdge(source="a", target="b")],
            entry="a", terminal_states=["b"],
        )
        with pytest.raises(CompileError, match="cannot consume"):
            compile_graph(graph)


def test_write_without_authority_boundary_rejected() -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[node("w", NodeClass.WRITE, "EXECUTE_ACTION", effect_type=EffectType.MOVE_MONEY)],
        edges=[], entry="w", terminal_states=["w"],
    )
    with pytest.raises(CompileError, match="authority boundary"):
        compile_graph(graph)


def test_irreversible_write_without_idempotency_rejected() -> None:
    from valo_workflow_isa.contracts import AuthorityRequirements, NodePolicies

    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[WorkflowNode(
            id="w", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE,
            effect_type=EffectType.MOVE_MONEY,
            policies=NodePolicies(authority=AuthorityRequirements(capability="PAY", scope=["a"])),
        )],
        edges=[], entry="w", terminal_states=["w"],
    )
    with pytest.raises(CompileError, match="idempotency"):
        compile_graph(graph)


def test_probabilistic_to_write_direct_edge_rejected() -> None:
    from valo_workflow_isa.contracts import AuthorityRequirements, NodePolicies

    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[
            node("p", NodeClass.DECIDE, "EVALUATE_RULE", determinism=Determinism.PROBABILISTIC, outputs=[TypedRef(name="recipient", type="Candidate<Recipient>")], config={"model": "m", "confidence": 0.8}),
            WorkflowNode(
                id="w", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE,
                effect_type=EffectType.MOVE_MONEY,
                inputs=[TypedRef(name="recipient", type="Confirmed<Recipient>")],
                policies=NodePolicies(authority=AuthorityRequirements(capability="PAY", scope=["a"]), idempotency=__import__("valo_workflow_isa").contracts.IdempotencyPolicy(require_key=True)),
            ),
        ],
        edges=[WorkflowEdge(source="p", target="w")],
        entry="p", terminal_states=["w"],
    )
    with pytest.raises(CompileError, match="probabilistic"):
        compile_graph(graph)


def test_cycle_without_termination_rejected() -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[node("a"), node("b")],
        edges=[WorkflowEdge(source="a", target="b"), WorkflowEdge(source="b", target="a")],
        entry="a", terminal_states=["a"],
    )
    with pytest.raises(CompileError, match="cycle"):
        compile_graph(graph)


def test_loop_with_termination_compiles() -> None:
    from valo_workflow_isa.contracts import ControlOpcode

    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={"done": "bool"},
        nodes=[
            node("loop", NodeClass.COMPUTE, ControlOpcode.LOOP.value, outputs=[TypedRef(name="continue", type="bool")], config={"condition": "true"}),
            node("body", NodeClass.COMPUTE, "CALCULATE", outputs=[TypedRef(name="work", type="bool")], config={"expression": "1"}),
            node("exit", NodeClass.COMPUTE, "CALCULATE", outputs=[TypedRef(name="done", type="bool")], config={"expression": "1"}),
        ],
        edges=[
            WorkflowEdge(source="loop", target="body", edge_type=EdgeType.TRUE, condition="continue == true"),
            WorkflowEdge(source="body", target="loop", edge_type=EdgeType.NEXT),
            WorkflowEdge(source="loop", target="exit", edge_type=EdgeType.FALSE, condition="continue == false"),
        ],
        entry="loop", terminal_states=["exit"],
    )
    compile_graph(graph)


def test_compensation_to_unknown_node_rejected() -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[node("a", compensation_ref="ghost")],
        edges=[], entry="a", terminal_states=["a"],
    )
    with pytest.raises(CompileError, match="compensation_ref"):
        compile_graph(graph)


def test_unknown_opcode_rejected() -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[node("a", opcode="NOT_A_REAL_OPCODE")],
        edges=[], entry="a", terminal_states=["a"],
    )
    with pytest.raises(CompileError, match="unknown opcode"):
        compile_graph(graph)


def test_opcode_node_class_mismatch_rejected() -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[node("a", NodeClass.COMPUTE, "READ_STATE")],
        edges=[], entry="a", terminal_states=["a"],
    )
    with pytest.raises(CompileError, match="requires node_class"):
        compile_graph(graph)


def test_effect_invalid_for_node_class_rejected() -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[node("a", NodeClass.DECIDE, "EVALUATE_RULE", effect_type=EffectType.MOVE_MONEY)],
        edges=[], entry="a", terminal_states=["a"],
    )
    with pytest.raises(CompileError, match="effect"):
        compile_graph(graph)


def test_output_not_produced_rejected() -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={"required_out": "int"},
        nodes=[node("a", outputs=[TypedRef(name="other", type="int")])],
        edges=[], entry="a", terminal_states=["a"],
    )
    with pytest.raises(CompileError, match="output"):
        compile_graph(graph)


def test_terminal_with_forward_successor_rejected() -> None:
    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[node("a"), node("b")],
        edges=[WorkflowEdge(source="a", target="b")],
        entry="a", terminal_states=["a", "b"],
    )
    with pytest.raises(CompileError, match="forward successors"):
        compile_graph(graph)


def test_halt_must_be_terminal() -> None:
    from valo_workflow_isa.contracts import ControlOpcode

    graph = WorkflowGraph(
        id="g", version="1", input_schema={}, output_schema={},
        nodes=[
            node("h", NodeClass.COMPUTE, ControlOpcode.HALT.value),
            node("after"),
        ],
        edges=[WorkflowEdge(source="h", target="after")],
        entry="h", terminal_states=["h"],
    )
    with pytest.raises(CompileError, match="HALT"):
        compile_graph(graph)
