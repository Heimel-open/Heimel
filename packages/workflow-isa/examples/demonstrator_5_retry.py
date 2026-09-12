"""Demonstrator 5: Retry / Idempotency.

A WRITE times out after the external effect may already have happened. The
runtime must NOT blindly re-execute: the idempotency key plus
verification/reconciliation decide the next step. Gateway detection alone does
not establish a verified effect, so the node defers without a second external
call pending a governed independent reconciliation path.
"""

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
from valo_workflow_isa.testing import (
    DictKernel,
    FakeBaro,
    FakeGateway,
    FakeReht,
    FakeVeritas,
)


def build_graph() -> WorkflowGraph:
    exec_node = WorkflowNode(
        id="exec", opcode="EXECUTE_ACTION", node_class=NodeClass.WRITE,
        effect_type=EffectType.ALLOCATE_RESOURCE,
        inputs=[TypedRef(name="authorized", type="Authorized<Action>")],
        outputs=[TypedRef(name="done", type="Confirmed<Action>")],
        policies=NodePolicies(
            authority=AuthorityRequirements(capability="BOOK", scope=["booking-1"]),
            idempotency=IdempotencyPolicy(require_key=True, key_source="authorized", verify_before_replay=True),
            retry=RetryPolicy(max_attempts=2, retry_after_timeout=True),
        ),
        config={"target": "booking-1", "actor": "agent-a", "identity_id": "id-agent", "capability": "BOOK", "action_type": "BOOK", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"},
    )
    return WorkflowGraph(
        id="retry", version="1", input_schema={}, output_schema={"done": "Confirmed<Action>"},
        nodes=[
            WorkflowNode(id="prep", opcode="PREPARE_ACTION", node_class=NodeClass.COMPUTE, outputs=[TypedRef(name="action", type="Candidate<Action>")], config={"target": "booking-1", "actor": "agent-a", "identity_id": "id-agent", "capability": "BOOK", "action_type": "BOOK", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"}),
            WorkflowNode(id="auth", opcode="AUTHORIZE_ACTION", node_class=NodeClass.WRITE, effect_type=EffectType.EXERCISE_AUTHORITY, inputs=[TypedRef(name="action", type="Candidate<Action>")], outputs=[TypedRef(name="authorized", type="Authorized<Action>")], policies=NodePolicies(authority=AuthorityRequirements(capability="BOOK", scope=["booking-1"]), idempotency=IdempotencyPolicy(require_key=True)), config={"target": "booking-1", "actor": "agent-a", "identity_id": "id-agent", "capability": "BOOK", "action_type": "BOOK", "kernel_event_type": "EXTERNAL_EFFECT_OBSERVED"}),
            exec_node,
        ],
        edges=[WorkflowEdge(source="prep", target="auth"), WorkflowEdge(source="auth", target="exec")],
        entry="prep", terminal_states=["exec"],
    )


def run() -> dict:
    kernel = DictKernel()
    kernel.register_entity("booking-1", state="OPEN")
    kernel.register_identity("id-agent", "agent-a", verified=True)
    kernel.grant_authority("agent-a", "BOOK", ["booking-1"])

    # The gateway records the external effect then loses the response (timeout
    # after the effect may have happened).
    gateway = FakeGateway(fail_after_execute=True)

    backend = ReferenceBackend()
    engine = RuntimeEngine(
        kernel,
        FakeReht(),
        gateway,
        FakeVeritas(),
        FakeBaro(),
        backend=backend,
        tenant_id="tenant-a",
    )
    instance = engine.start(build_graph(), {})

    assert instance.status == WorkflowStatus.DEFERRED, "unknown effect outcome must defer"
    assert len(gateway.executions) == 1, "the external effect must NOT be re-executed"
    assert gateway.replayed == []
    events = backend.events_for(instance.instance_id)
    assert all(event["event_type"] != "EffectVerified" for event in events)
    assert kernel.events == []
    resumed = engine.resume(instance, {"effect_verified": True})
    assert resumed.status == WorkflowStatus.DEFERRED
    assert len(gateway.executions) == 1
    return {
        "status": instance.status.value,
        "external_calls": len(gateway.executions),
        "effect_verified": False,
    }


def test_demonstrator_5_retry_idempotency() -> None:
    result = run()
    assert result["status"] == "DEFERRED"
    assert result["external_calls"] == 1
    assert result["effect_verified"] is False


if __name__ == "__main__":
    print(run())
