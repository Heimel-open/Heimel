"""Demonstrator 5: govern the space, not the worker.

Kernel projects only the job and purpose needed by a work unit. A replaceable
worker returns a candidate action. Deterministic conformance passes. Unrelated
tenant state may change without wasting the result; relevant state drift
invalidates it before execution.
"""

from __future__ import annotations

from datetime import timedelta

from valo_kernel import (
    CandidateKind,
    ConformanceOutcome,
    KernelEngine,
    ProjectionSelector,
    ProposedAction,
    Purpose,
    TimeWindow,
    WorkspaceCapabilitySpec,
    WorkspaceSpec,
    bind_workspace_execution,
    compile_governed_workspace,
    create_candidate_result,
    evaluate_candidate_conformance,
    utcnow,
)
from valo_kernel.contracts import CanonicalEvent, EntityType, EventType


def _entity(tenant: str, entity_id: str, state: str) -> CanonicalEvent:
    return CanonicalEvent(
        event_id=f"entity-{entity_id}",
        event_type=EventType.ENTITY_REGISTERED,
        tenant_id=tenant,
        subject=entity_id,
        source="kernel",
        payload={
            "entity": {
                "entity_id": entity_id,
                "entity_type": EntityType.JOB,
                "tenant_id": tenant,
                "state": state,
                "provenance": {
                    "source_type": "system",
                    "source_id": "bootstrap",
                    "source_system": "valo-kernel",
                },
            }
        },
    )


def run() -> dict[str, str]:
    tenant = "demo-5"
    engine = KernelEngine(tenant)
    now = utcnow()
    engine.append(_entity(tenant, "job-1", "READY"))
    engine.append(_entity(tenant, "job-unrelated", "READY"))

    purpose = Purpose(
        purpose_id="reserve-job",
        purpose_type="reservation",
        scope=["job-1"],
        basis="customer-request",
        permitted_data=["entities:job-1"],
        permitted_actions=["BOOK"],
        validity=TimeWindow(
            valid_from=now - timedelta(minutes=1),
            valid_until=now + timedelta(hours=1),
        ),
    )
    engine.append(
        CanonicalEvent(
            event_id="purpose-reserve-job",
            event_type=EventType.PURPOSE_REGISTERED,
            tenant_id=tenant,
            subject=purpose.purpose_id,
            source="kernel",
            payload={"purpose": purpose},
        )
    )

    spec = WorkspaceSpec(
        workspace_id="workspace-job-1",
        work_unit_id="work-job-1",
        tenant_id=tenant,
        purpose_id=purpose.purpose_id,
        selectors=(ProjectionSelector(collection="entities", object_ids=("job-1",)),),
        capabilities=(
            WorkspaceCapabilitySpec(
                capability="BOOK",
                target_refs=("job-1",),
                allowed_effects=("reserve",),
            ),
        ),
        allowed_output_kinds=(CandidateKind.EXTERNAL_ACTION,),
        expires_at=now + timedelta(minutes=30),
    )
    workspace = compile_governed_workspace(
        engine.state(),
        spec,
        source_event_position=engine.sequence(),
        moment=now,
    )
    action = ProposedAction(
        action_id="book-job-1",
        capability="BOOK",
        target="job-1",
        purpose_id=purpose.purpose_id,
        declared_effects=("reserve",),
    )
    candidate = create_candidate_result(
        candidate_id="candidate-1",
        invocation_id="invocation-1",
        worker_id="replaceable-worker",
        workspace_id=workspace.spec.workspace_id,
        workspace_digest=workspace.workspace_digest,
        output_kind=CandidateKind.EXTERNAL_ACTION,
        proposed_actions=(action,),
    )
    initial = evaluate_candidate_conformance(
        workspace,
        candidate,
        engine.state(),
        moment=now,
    )
    binding = bind_workspace_execution(
        workspace,
        candidate,
        initial,
        action_id=action.action_id,
    )

    engine.append(
        CanonicalEvent(
            event_id="unrelated-change",
            event_type=EventType.ENTITY_UPDATED,
            tenant_id=tenant,
            subject="job-unrelated",
            source="kernel",
            payload={"entity_id": "job-unrelated", "state": "BUSY"},
        )
    )
    unrelated = evaluate_candidate_conformance(
        workspace,
        candidate,
        engine.state(),
    )
    engine.append(
        CanonicalEvent(
            event_id="relevant-change",
            event_type=EventType.ENTITY_UPDATED,
            tenant_id=tenant,
            subject="job-1",
            source="kernel",
            payload={"entity_id": "job-1", "state": "BUSY"},
        )
    )
    relevant = evaluate_candidate_conformance(
        workspace,
        candidate,
        engine.state(),
    )

    assert initial.outcome == ConformanceOutcome.PASS
    assert unrelated.outcome == ConformanceOutcome.PASS
    assert relevant.outcome == ConformanceOutcome.DEFER
    return {
        "initial": initial.outcome.value,
        "unrelated_change": unrelated.outcome.value,
        "relevant_change": relevant.outcome.value,
        "execution_binding": binding.proposed_action_digest,
    }


def test_demonstrator_5_governed_space() -> None:
    result = run()
    assert result["initial"] == "PASS"
    assert result["unrelated_change"] == "PASS"
    assert result["relevant_change"] == "DEFER"


if __name__ == "__main__":
    print(run())
