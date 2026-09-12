"""Demonstrator 4: External Success != Verified Effect.

REHT ALLOWs. The Gateway returns success. Veritas observes the result. BARO
finds that the expected postcondition did not arise (payment transferred but
the invoice is still OPEN). The workflow must NOT complete: the kernel never
marks the postcondition verified. Result: FAILED.
"""

from __future__ import annotations

from valo_workflow_isa import (
    AuthorityRequirements,
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
)
from valo_workflow_isa.testing import (
    DictKernel,
    FakeBaro,
    FakeGateway,
    FakeReht,
    FakeVeritas,
)


def build_graph() -> WorkflowGraph:
    return WorkflowGraph(
        id="mismatch", version="1", input_schema={}, output_schema={"done": "Confirmed<Action>"},
        nodes=[
            WorkflowNode(id="prep", opcode="PREPARE_ACTION", node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="action", type="Candidate<Action>")], config={"target": "invoice-1", "actor": "agent-a", "identity_id": "id-agent", "capability": "PAY", "action_type": "PAY", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"}),
            WorkflowNode(id="auth", opcode="AUTHORIZE_ACTION", node_class=NodeClass.WRITE, effect_type=EffectType.EXERCISE_AUTHORITY, inputs=[TypedRef(name="action", type="Candidate<Action>")], outputs=[TypedRef(name="authorized", type="Authorized<Action>")], policies=NodePolicies(authority=AuthorityRequirements(capability="PAY", scope=["invoice-1"]), idempotency=IdempotencyPolicy(require_key=True)), config={"target": "invoice-1", "actor": "agent-a", "identity_id": "id-agent", "capability": "PAY", "action_type": "PAY", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"}),
            WorkflowNode(id="exec", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE, effect_type=EffectType.MOVE_MONEY, inputs=[TypedRef(name="authorized", type="Authorized<Action>")], outputs=[TypedRef(name="done", type="Confirmed<Action>")], policies=NodePolicies(authority=AuthorityRequirements(capability="PAY", scope=["invoice-1"]), idempotency=IdempotencyPolicy(require_key=True)), config={"target": "invoice-1", "actor": "agent-a", "identity_id": "id-agent", "capability": "PAY", "action_type": "PAY", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED", "postconditions": {"invoice-1": "PAID"}}),
        ],
        edges=[WorkflowEdge(source="prep", target="auth"), WorkflowEdge(source="auth", target="exec")],
        entry="prep", terminal_states=["exec"],
    )


def run() -> dict:
    kernel = DictKernel()
    kernel.register_entity("invoice-1", state="OPEN")
    kernel.register_identity("id-agent", "agent-a", verified=True)
    kernel.grant_authority("agent-a", "PAY", ["invoice-1"])

    # external API answers success; the observed reality keeps the invoice OPEN
    veritas = FakeVeritas(observed={"invoice-1": "OPEN"})
    baro = FakeBaro()

    engine = RuntimeEngine(kernel, FakeReht(), FakeGateway(success=True), veritas, baro, tenant_id="tenant-a")
    instance = engine.start(build_graph(), {})

    assert instance.status != WorkflowStatus.COMPLETED, "external success alone must not complete the workflow"
    assert instance.status == WorkflowStatus.FAILED
    assert "postcondition" in instance.errors.get("exec", "").lower()
    return {"status": instance.status.value, "error": instance.errors.get("exec")}


def test_demonstrator_4_external_mismatch() -> None:
    result = run()
    assert result["status"] == "FAILED"


if __name__ == "__main__":
    print(run())
