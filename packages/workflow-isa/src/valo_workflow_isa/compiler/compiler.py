from __future__ import annotations

from ..contracts.common import (
    ControlOpcode,
    Determinism,
    NodeClass,
    PrimitiveOpcode,
)
from ..contracts.graph import WorkflowGraph
from ..effects.system import IRREVERSIBLE_EFFECTS, validate_effect
from ..graph.invariants import (
    graph_inputs_satisfy,
    producer_types_for_input,
    reachable_from,
    successors,
)
from ..opcodes.primitives import opcode_node_class
from ..types.system import can_consume
from .errors import CompileError


def compile_graph(graph: WorkflowGraph) -> None:
    """Static compile/validate. Fail closed: raises CompileError listing every
    violation found. A graph must compile before it can run."""
    errors: list[str] = []
    node_map = graph.node_map()

    # 1. opcode/node_class consistency + effect declaration validity
    for node in graph.nodes:
        if node.opcode not in set(ControlOpcode) and node.opcode not in set(PrimitiveOpcode):
            errors.append(f"node {node.id}: unknown opcode {node.opcode}")
            continue
        spec_node_class = opcode_node_class(node.opcode) if node.opcode in set(PrimitiveOpcode) else None
        if spec_node_class is not None and spec_node_class != node.node_class:
            errors.append(
                f"node {node.id}: opcode {node.opcode} requires node_class "
                f"{spec_node_class.value}, got {node.node_class.value}"
            )
        try:
            validate_effect(node.node_class, node.effect_type)
        except ValueError as exc:
            errors.append(f"node {node.id}: {exc}")

    # 2. no unreachable nodes
    reachable = reachable_from(graph, graph.entry)
    for node in graph.nodes:
        if node.id not in reachable:
            errors.append(f"node {node.id}: unreachable from entry")

    # 3. all refs exist (edges validated by model; compensation_ref here)
    for node in graph.nodes:
        if node.compensation_ref is not None and node.compensation_ref not in node_map:
            errors.append(f"node {node.id}: compensation_ref to unknown node {node.compensation_ref}")

    # 4. all inputs have a producer or a graph input
    for node in graph.nodes:
        missing = graph_inputs_satisfy(graph, node.id)
        for name in missing:
            errors.append(f"node {node.id}: input {name} has no producer and is not a graph input")

    # 5. all required outputs produced
    for name, expected_type in graph.output_schema.items():
        producers = [
            n.id
            for n in graph.nodes
            if any(o.name == name and can_consume(o.type, expected_type) for o in n.outputs)
        ]
        if not producers:
            errors.append(f"output {name}: no node produces a value of type {expected_type}")

    # 6. no WRITE without authorization boundary
    for node in graph.nodes:
        if node.node_class == NodeClass.WRITE and node.policies.authority is None:
            errors.append(
                f"node {node.id}: WRITE requires an authority boundary (policies.authority)"
            )

    # 7. no irreversible WRITE without idempotency
    for node in graph.nodes:
        if (
            node.node_class == NodeClass.WRITE
            and node.effect_type in IRREVERSIBLE_EFFECTS
            and not node.policies.idempotency.require_key
        ):
            errors.append(
                f"node {node.id}: irreversible effect {node.effect_type.value} requires idempotency"
            )

    # 8. no compensation to unknown node (covered in 3)

    # 9. no probabilistic -> WRITE direct edge
    for edge in graph.edges:
        source = node_map[edge.source]
        target = node_map[edge.target]
        if source.determinism == Determinism.PROBABILISTIC and target.node_class == NodeClass.WRITE:
            errors.append(
                f"edge {edge.source}->{edge.target}: probabilistic output cannot feed a WRITE directly"
            )

    # 10. all terminal paths defined: every terminal_state must be a dead end
    for terminal in graph.terminal_states:
        out = successors(graph, terminal)
        if any(e.edge_type.value in ("NEXT", "TRUE", "FALSE") for e in out):
            errors.append(f"terminal {terminal}: has forward successors")

    # 11. type compatibility between nodes
    for node in graph.nodes:
        for ref in node.inputs:
            producers = producer_types_for_input(graph, node.id, ref.name)
            if not producers and ref.name in graph.input_schema and not can_consume(
                graph.input_schema[ref.name], ref.type
            ):
                errors.append(
                    f"node {node.id}: graph input {ref.name} type {graph.input_schema[ref.name]} "
                    f"cannot satisfy {ref.type}"
                )
                continue
            for producer_id, produced_type in producers:
                if not can_consume(produced_type, ref.type):
                    errors.append(
                        f"node {node.id}: input {ref.name} cannot consume "
                        f"{producer_id}:{produced_type} as {ref.type}"
                    )

    # 12. no cycle without termination condition (explicit LOOP/DECIDE exit)
    for cycle in _find_cycles(graph):
        has_termination = any(
            node_map[n].opcode in ("LOOP", "BRANCH") or node_map[n].node_class == NodeClass.DECIDE
            for n in cycle
        )
        if not has_termination:
            errors.append(
                f"cycle {sorted(cycle)} lacks a termination condition (LOOP/BRANCH/DECIDE)"
            )

    # 13. no HALT bypass: HALT nodes must not be bypassed by forward flow
    for node in graph.nodes:
        if node.opcode == ControlOpcode.HALT.value:
            # HALT is terminal by definition; successors of HALT rejected
            for edge in successors(graph, node.id):
                if edge.edge_type.value in ("NEXT", "TRUE", "FALSE"):
                    errors.append(f"node {node.id}: HALT must have no forward successors")

    if errors:
        raise CompileError("; ".join(errors))


def _find_cycles(graph: WorkflowGraph) -> list[list[str]]:
    """Simple cycle detection (each back-edge yields one cycle path)."""
    cycles: list[list[str]] = []
    visited: set[str] = set()
    stack: list[str] = []
    on_stack: set[str] = set()
    node_map = graph.node_map()

    def dfs(node_id: str) -> None:
        visited.add(node_id)
        on_stack.add(node_id)
        stack.append(node_id)
        for edge in successors(graph, node_id):
            target = edge.target
            if target in on_stack:
                idx = stack.index(target)
                cycle = stack[idx:]
                if cycle not in cycles:
                    cycles.append(list(cycle))
            elif target not in visited:
                dfs(target)
        stack.pop()
        on_stack.discard(node_id)

    for node_id in node_map:
        if node_id not in visited:
            dfs(node_id)
    return cycles
