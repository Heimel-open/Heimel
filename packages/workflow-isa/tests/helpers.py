from __future__ import annotations

from valo_workflow_isa.contracts import (
    AuthorityRequirements,
    EffectType,
    IdempotencyPolicy,
    NodeClass,
    NodePolicies,
    TypedRef,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
)


def linear_graph(
    graph_id: str,
    opcodes: list[str],
    *,
    entry: str | None = None,
    terminal: str | None = None,
    version: str = "1",
) -> WorkflowGraph:
    nodes = [
        WorkflowNode(id=f"n{i}", opcode=op, node_class=_node_class_for(op), config={"target": "entity-x"})
        for i, op in enumerate(opcodes)
    ]
    edges = [WorkflowEdge(source=nodes[i].id, target=nodes[i + 1].id) for i in range(len(nodes) - 1)]
    return WorkflowGraph(
        id=graph_id,
        version=version,
        input_schema={},
        output_schema={},
        nodes=nodes,
        edges=edges,
        entry=entry or nodes[0].id,
        terminal_states=[terminal or nodes[-1].id],
    )


def _node_class_for(opcode: str) -> NodeClass:
    from valo_workflow_isa.contracts import ControlOpcode
    from valo_workflow_isa.opcodes.primitives import opcode_node_class

    if opcode in set(ControlOpcode):
        return NodeClass.COMPUTE
    spec = opcode_node_class(opcode)
    return spec if spec is not None else NodeClass.COMPUTE


def write_node(
    node_id: str,
    *,
    opcode: str,
    effect: EffectType,
    capability: str,
    target: str,
    actor: str,
    require_key: bool = False,
    verify_before_replay: bool = False,
    inputs: list[TypedRef] | None = None,
    outputs: list[TypedRef] | None = None,
    config: dict | None = None,
) -> WorkflowNode:
    return WorkflowNode(
        id=node_id,
        opcode=opcode,
        node_class=NodeClass.WRITE,
        inputs=inputs or [TypedRef(name="action", type="Authorized<Action>")],
        outputs=outputs or [TypedRef(name="result", type="Confirmed<Action>")],
        effect_type=effect,
        policies=NodePolicies(
            authority=AuthorityRequirements(capability=capability, scope=[target]),
            idempotency=IdempotencyPolicy(
                require_key=require_key, verify_before_replay=verify_before_replay, key_source="action"
            ),
        ),
        config={
            "target": target,
            "actor": actor,
            "action_type": "EXECUTE",
            "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED",
            **(config or {}),
        },
    )
