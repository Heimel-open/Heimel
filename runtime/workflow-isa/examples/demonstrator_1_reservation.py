"""Demonstrator 1: Resource Reservation.

Graph: READ_STATE -> ASSERT_STATE -> PREPARE_ACTION -> AUTHORIZE_ACTION
     -> RESERVE_RESOURCE -> VERIFY_EXECUTION.

Two parallel workflow instances attempt to reserve the same worker through the
real valo_kernel. The kernel's resource state is authoritative and append-only;
only one reservation can succeed. Proves: kernel integration, authority
boundary, concurrency, deterministic flow.
"""

from __future__ import annotations

from datetime import timedelta

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
from valo_workflow_isa.ports import ValoKernelAdapter
from valo_workflow_isa.testing import FakeBaro, FakeReht, FakeVeritas

# Real gateway/veritas/baro fakes; kernel is the real valo_kernel.


class Gateway:
    def __init__(self) -> None:
        self.executions = 0
        self.keys: set[str] = set()

    def execute(self, binding, action_contract, idempotency_key):
        from valo_workflow_isa.ports import ExecutionResult

        if idempotency_key:
            if idempotency_key in self.keys:
                return ExecutionResult(success=True, external_id="replayed", receipt_ref="receipt-replay")
            self.keys.add(idempotency_key)
        self.executions += 1
        return ExecutionResult(success=True, external_id=f"ext-{self.executions}", receipt_ref=f"receipt-{self.executions}", payload={"reserved": True})

    def has_effect(self, idempotency_key: str) -> bool:
        return idempotency_key in self.keys


def build_graph() -> WorkflowGraph:
    return WorkflowGraph(
        id="reservation",
        version="1",
        input_schema={},
        output_schema={"done": "Confirmed<Reservation>"},
        nodes=[
            WorkflowNode(
                id="read", opcode="READ_STATE", node_class=NodeClass.READ,
                outputs=[TypedRef(name="state", type="Verified<Resource>")],
                config={"target": "electrician-1"},
            ),
            WorkflowNode(
                id="assert", opcode="ASSERT_STATE", node_class=NodeClass.READ,
                inputs=[TypedRef(name="state", type="Verified<Resource>")],
                outputs=[TypedRef(name="ready", type="bool")],
                preconditions=["state == AVAILABLE"],
            ),
            WorkflowNode(
                id="prep", opcode="PREPARE_ACTION", node_class=NodeClass.COMPUTE,
                outputs=[TypedRef(name="action", type="Candidate<Action>")],
                config={
                    "target": "electrician-1",
                    "actor": "electrician-1",
                    "capability": "BOOK",
                    "action_type": "RESERVE_RESOURCE",
                    "kernel_event_type": "RESOURCE_RESERVED",
                    "requested_transition": {
                        "reservation": {
                            "reservation_id": "r-electrical-job-1",
                            "resource_id": "electrician-1",
                            "holder": "electrician-1",
                            "tenant_id": "demo-1",
                            "purpose": "job-1",
                        }
                    },
                },
            ),
            WorkflowNode(
                id="auth", opcode="AUTHORIZE_ACTION", node_class=NodeClass.WRITE,
                effect_type=EffectType.EXERCISE_AUTHORITY,
                inputs=[TypedRef(name="action", type="Candidate<Action>")],
                outputs=[TypedRef(name="authorized", type="Authorized<Action>")],
                policies=NodePolicies(
                    authority=AuthorityRequirements(capability="BOOK", scope=["electrician-1"]),
                    idempotency=IdempotencyPolicy(require_key=True),
                ),
                config={"target": "electrician-1", "actor": "electrician-1", "identity_id": "id-electrician", "capability": "BOOK", "action_type": "RESERVE_RESOURCE", "kernel_event_type": "RESOURCE_RESERVED"},
            ),
            WorkflowNode(
                id="reserve", opcode="RESERVE_RESOURCE", node_class=NodeClass.WRITE,
                effect_type=EffectType.ALLOCATE_RESOURCE,
                inputs=[TypedRef(name="authorized", type="Authorized<Action>")],
                outputs=[TypedRef(name="done", type="Confirmed<Reservation>")],
                policies=NodePolicies(
                    authority=AuthorityRequirements(capability="BOOK", scope=["electrician-1"]),
                    idempotency=IdempotencyPolicy(require_key=True, key_source="authorized"),
                ),
                config={"target": "electrician-1", "actor": "electrician-1", "identity_id": "id-electrician", "resource_id": "electrician-1", "purpose": "job-1", "kernel_event_type": "RESOURCE_RESERVED"},
            ),
            WorkflowNode(
                id="verify", opcode="VERIFY_EXECUTION", node_class=NodeClass.READ,
                inputs=[TypedRef(name="done", type="Confirmed<Reservation>")],
                outputs=[TypedRef(name="verified", type="Confirmed<Reservation>")],
                config={},
            ),
        ],
        edges=[
            WorkflowEdge(source="read", target="assert"),
            WorkflowEdge(source="assert", target="prep"),
            WorkflowEdge(source="prep", target="auth"),
            WorkflowEdge(source="auth", target="reserve"),
            WorkflowEdge(source="reserve", target="verify"),
        ],
        entry="read",
        terminal_states=["verify"],
    )


def run() -> dict:
    from valo_kernel import KernelEngine
    from valo_kernel.contracts import (
        Authority,
        CanonicalEvent,
        Entity,
        EntityType,
        EventType,
        IdentityClaim,
        Provenance,
        TimeWindow,
        VerificationStatus,
        utcnow,
    )

    kernel = KernelEngine("demo-1")
    now = utcnow()
    prov = Provenance(source_type="system", source_id="demo", source_system="valo-kernel")

    for entity_id, etype, state in [
        ("customer-1", EntityType.PERSON, None),
        ("electrician-1", EntityType.PERSON, None),
        ("job-1", EntityType.JOB, "READY"),
    ]:
        kernel.append(CanonicalEvent(event_id=f"entity-{entity_id}", event_type=EventType.ENTITY_REGISTERED, tenant_id="demo-1", subject=entity_id, source="kernel", effective_at=now, payload={"entity": Entity(entity_id=entity_id, entity_type=etype, tenant_id="demo-1", state=state, provenance=prov)}))

    kernel.append(CanonicalEvent(event_id="res-electrician", event_type=EventType.RESOURCE_REGISTERED, tenant_id="demo-1", subject="electrician-1", source="kernel", effective_at=now, payload={"resource": {"resource_id": "electrician-1", "resource_type": "personnel", "tenant_id": "demo-1", "capacity": 1}}))

    kernel.append(CanonicalEvent(event_id="id-electrician", event_type=EventType.IDENTITY_CLAIMED, tenant_id="demo-1", subject="electrician-1", source="kernel", effective_at=now, payload={"identity": IdentityClaim(identity_id="id-electrician", entity_id="electrician-1", tenant_id="demo-1", claim_type="credential_id", value="cert-42", verification_status=VerificationStatus.VERIFIED)}))

    kernel.append(CanonicalEvent(event_id="auth-book", event_type=EventType.AUTHORITY_GRANTED, tenant_id="demo-1", subject="electrician-1", source="kernel", effective_at=now, payload={"authority": Authority(authority_id="auth-book", principal="electrician-1", capability="BOOK", scope=["electrician-1"], basis="schedule-policy", validity=TimeWindow(valid_from=now, valid_until=now + timedelta(days=1)))}))

    adapter = ValoKernelAdapter(kernel, "demo-1")
    gateway = Gateway()
    ports = (adapter, FakeReht(), gateway, FakeVeritas(), FakeBaro())
    graph = build_graph()

    e1 = RuntimeEngine(*ports, tenant_id="demo-1")
    e2 = RuntimeEngine(*ports, tenant_id="demo-1")
    i1 = e1.start(graph, {})
    i2 = e2.start(graph, {})

    completed = [i for i in (i1, i2) if i.status == WorkflowStatus.COMPLETED]
    assert len(completed) == 1, f"exactly one reservation must succeed, got {len(completed)}"
    assert kernel.state().resources["electrician-1"].state.value == "RESERVED"
    return {"completed": len(completed), "resource_state": kernel.state().resources["electrician-1"].state.value}


def test_demonstrator_1_reservation() -> None:
    result = run()
    assert result["completed"] == 1
    assert result["resource_state"] == "RESERVED"


if __name__ == "__main__":
    print(run())
