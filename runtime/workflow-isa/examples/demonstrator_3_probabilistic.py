"""Demonstrator 3: Probabilistic Boundary.

A probabilistic node proposes a recipient. A graph that tries to send it
directly to WRITE is rejected by the static compiler. A valid graph must first
produce explicit verification/admission before any WRITE.

Two parts:
  - invalid graph  -> CompileError (probabilistic -> WRITE direct edge)
  - valid graph    -> probabilistic EVALUATE_RULE -> RECONCILE (admission)
                      -> PREPARE_ACTION -> AUTHORIZE_ACTION -> EXECUTE_ACTION
"""

from __future__ import annotations

import pytest

from valo_workflow_isa import (
    AuthorityRequirements,
    CompileError,
    Determinism,
    EffectType,
    IdempotencyPolicy,
    NodeClass,
    NodePolicies,
    RuntimeEngine,
    TypedRef,
    WorkflowEdge,
    WorkflowGraph,
    WorkflowNode,
    WorkflowStatus,
    compile_graph,
)
from valo_workflow_isa.contracts import EdgeType
from valo_workflow_isa.testing import (
    DictKernel,
    FakeBaro,
    FakeGateway,
    FakeReht,
    FakeVeritas,
)


def _probabilistic_node() -> WorkflowNode:
    return WorkflowNode(
        id="p", opcode="EVALUATE_RULE", node_class=NodeClass.DECIDE,
        determinism=Determinism.PROBABILISTIC,
        outputs=[TypedRef(name="recipient", type="Candidate<Recipient>")],
        config={"model": "vaig-v3", "model_version": "3", "confidence": 0.82, "source_context": "proposal-7", "rule": "true"},
    )


def invalid_graph() -> WorkflowGraph:
    return WorkflowGraph(
        id="invalid", version="1", input_schema={}, output_schema={},
        nodes=[
            _probabilistic_node(),
            WorkflowNode(
                id="w", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE,
                effect_type=EffectType.MOVE_MONEY,
                inputs=[TypedRef(name="recipient", type="Confirmed<Recipient>")],
                outputs=[TypedRef(name="done", type="any")],
                policies=NodePolicies(
                    authority=AuthorityRequirements(capability="PAY", scope=["acct"]),
                    idempotency=IdempotencyPolicy(require_key=True),
                ),
                config={"target": "acct", "actor": "agent-a", "capability": "PAY", "action_type": "PAY", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
            ),
        ],
        edges=[WorkflowEdge(source="p", target="w")],
        entry="p", terminal_states=["w"],
    )


def valid_graph() -> WorkflowGraph:
    """The probabilistic proposal must pass explicit admission (RECONCILE)
    which upgrades it to a verified value before the WRITE boundary."""
    return WorkflowGraph(
        id="valid", version="1", input_schema={}, output_schema={"done": "Confirmed<Action>"},
        nodes=[
            _probabilistic_node(),
            WorkflowNode(id="admit", opcode="RECONCILE", node_class=NodeClass.COMPUTE, inputs=[TypedRef(name="recipient", type="Candidate<Recipient>")], outputs=[TypedRef(name="verified_recipient", type="Verified<Recipient>")], config={"proposed": "candidate"}),
            WorkflowNode(id="prep", opcode="PREPARE_ACTION", node_class=NodeClass.COMPUTE, inputs=[TypedRef(name="verified_recipient", type="Verified<Recipient>")], outputs=[TypedRef(name="action", type="Candidate<Action>")], config={"target": "acct", "actor": "agent-a", "capability": "PAY", "action_type": "PAY", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"}),
            WorkflowNode(id="auth", opcode="AUTHORIZE_ACTION", node_class=NodeClass.WRITE, effect_type=EffectType.EXERCISE_AUTHORITY, inputs=[TypedRef(name="action", type="Candidate<Action>")], outputs=[TypedRef(name="authorized", type="Authorized<Action>")], policies=NodePolicies(authority=AuthorityRequirements(capability="PAY", scope=["acct"]), idempotency=IdempotencyPolicy(require_key=True)), config={"target": "acct", "actor": "agent-a", "capability": "PAY", "action_type": "PAY", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"}),
            WorkflowNode(id="exec", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE, effect_type=EffectType.MOVE_MONEY, inputs=[TypedRef(name="authorized", type="Authorized<Action>")], outputs=[TypedRef(name="done", type="Confirmed<Action>")], policies=NodePolicies(authority=AuthorityRequirements(capability="PAY", scope=["acct"]), idempotency=IdempotencyPolicy(require_key=True)), config={"target": "acct", "actor": "agent-a", "capability": "PAY", "action_type": "PAY", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"}),
        ],
        edges=[
            WorkflowEdge(source="p", target="admit", edge_type=EdgeType.NEXT),
            WorkflowEdge(source="admit", target="prep"),
            WorkflowEdge(source="prep", target="auth"),
            WorkflowEdge(source="auth", target="exec"),
        ],
        entry="p", terminal_states=["exec"],
    )


def run() -> dict:
    # invalid graph is rejected at compile time
    with pytest.raises(CompileError):
        compile_graph(invalid_graph())

    # valid graph compiles and the probabilistic value never reaches WRITE
    # directly; it is admitted first.
    kernel = DictKernel()
    kernel.register_entity("acct", state="OPEN")
    kernel.register_identity("id-agent", "agent-a", verified=True)
    kernel.grant_authority("agent-a", "PAY", ["acct"])

    engine = RuntimeEngine(kernel, FakeReht(), FakeGateway(), FakeVeritas(), FakeBaro(), tenant_id="tenant-a")
    instance = engine.start(valid_graph(), {})
    assert instance.status == WorkflowStatus.COMPLETED
    admitted = instance.outputs["admit"]["verified_recipient"]
    from valo_workflow_isa.runtime.values import RuntimeValue

    payload = admitted.value if isinstance(admitted, RuntimeValue) else admitted
    assert payload["truth_status"] == "ADMITTED", "probabilistic output must be explicitly admitted"
    prob = instance.outputs["p"]["recipient"]
    prob_payload = prob.value if isinstance(prob, RuntimeValue) else prob
    assert "model" in prob_payload, "probabilistic output must carry model metadata"
    return {"invalid_rejected": True, "status": instance.status.value, "admitted": (admitted.value if isinstance(admitted, RuntimeValue) else admitted)["truth_status"]}


def test_demonstrator_3_probabilistic_boundary() -> None:
    result = run()
    assert result["invalid_rejected"] is True
    assert result["status"] == "COMPLETED"


if __name__ == "__main__":
    print(run())
