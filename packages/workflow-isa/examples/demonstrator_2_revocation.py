"""Demonstrator 2: Revoked Authority (mandatory negative test).

The workflow starts while authority is valid. Before the WRITE boundary the
authority is revoked in the kernel. The WRITE re-reads a fresh execution
context; the REHT port sees no authority and DENYs. No booking happens.
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
from valo_workflow_isa.contracts.common import canonical_digest
from valo_workflow_isa.ports import DecisionResult
from valo_workflow_isa.testing import (
    DictKernel,
    FakeBaro,
    FakeGateway,
    FakeVeritas,
)


class RevokingReht:
    """Authorizes the first boundary (AUTHORIZE_ACTION) while authority is
    still valid, then DENYs the execution boundary — authority was revoked in
    the kernel between the two."""

    def __init__(self) -> None:
        self.calls = 0

    def authorize(self, execution_context, action_contract):
        self.calls += 1
        if self.calls == 1:
            return DecisionResult(
                decision="ALLOW",
                clearance_ref="clearance-1",
                permit_ref="permit-1",
                execution_context_hash=canonical_digest(execution_context),
            )
        return DecisionResult(decision="DENY", reason="authority revoked before execution boundary")


def build_graph() -> WorkflowGraph:
    return WorkflowGraph(
        id="revocation", version="1", input_schema={}, output_schema={"done": "Confirmed<Action>"},
        nodes=[
            WorkflowNode(id="prep", opcode="PREPARE_ACTION", node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="action", type="Candidate<Action>")], config={"target": "booking-1", "actor": "agent-a", "identity_id": "id-agent", "capability": "BOOK", "action_type": "BOOK", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"}),
            WorkflowNode(id="auth", opcode="AUTHORIZE_ACTION", node_class=NodeClass.WRITE, effect_type=EffectType.EXERCISE_AUTHORITY, inputs=[TypedRef(name="action", type="Candidate<Action>")], outputs=[TypedRef(name="authorized", type="Authorized<Action>")], policies=NodePolicies(authority=AuthorityRequirements(capability="BOOK", scope=["booking-1"]), idempotency=IdempotencyPolicy(require_key=True)), config={"target": "booking-1", "actor": "agent-a", "identity_id": "id-agent", "capability": "BOOK", "action_type": "BOOK", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"}),
            WorkflowNode(id="exec", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE, effect_type=EffectType.ALLOCATE_RESOURCE, inputs=[TypedRef(name="authorized", type="Authorized<Action>")], outputs=[TypedRef(name="done", type="Confirmed<Action>")], policies=NodePolicies(authority=AuthorityRequirements(capability="BOOK", scope=["booking-1"]), idempotency=IdempotencyPolicy(require_key=True)), config={"target": "booking-1", "actor": "agent-a", "identity_id": "id-agent", "action_type": "BOOK", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"}),
        ],
        edges=[WorkflowEdge(source="prep", target="auth"), WorkflowEdge(source="auth", target="exec")],
        entry="prep", terminal_states=["exec"],
    )


def run() -> dict:
    kernel = DictKernel()
    kernel.register_entity("booking-1", state="OPEN")
    kernel.register_identity("id-agent", "agent-a", verified=True)
    kernel.grant_authority("agent-a", "BOOK", ["booking-1"])

    reht = RevokingReht()
    engine = RuntimeEngine(kernel, reht, FakeGateway(), FakeVeritas(), FakeBaro(), tenant_id="tenant-a")
    instance = engine.start(build_graph(), {})

    # authority revoked before the execution boundary -> DENY -> no booking
    assert instance.status == WorkflowStatus.FAILED, "workflow must fail when authority is revoked"
    assert reht.calls >= 2
    assert kernel.reservations == {}, "no booking may happen"
    return {"status": instance.status.value, "authorization_calls": reht.calls}


def test_demonstrator_2_revocation() -> None:
    result = run()
    assert result["status"] == "FAILED"


if __name__ == "__main__":
    print(run())
