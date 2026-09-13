"""Demonstrator 6: hardware-attested Governed Workspace.

A replaceable worker receives the same non-authoritative governed projection,
but the workspace is released only when a provider-neutral TEE attestation is
verified, fresh, measurement-compatible and valid for the workspace lifetime.
The attestation creates no authority; its digest is carried into the execution
binding for downstream REHT/Gateway/Veritas checks.
"""

from __future__ import annotations

from datetime import timedelta

from valo_kernel import (
    CandidateKind,
    ConformanceOutcome,
    EntityType,
    EventType,
    KernelEngine,
    ProjectionSelector,
    ProposedAction,
    Purpose,
    TimeWindow,
    WorkspaceCapabilitySpec,
    WorkspaceSpec,
    create_candidate_result,
    utcnow,
)
from valo_kernel.confidential_workspace import (
    AttestationStatus,
    ExecutionSubstrateRequirement,
    bind_attested_workspace_execution,
    compile_attested_governed_workspace,
    evaluate_attested_candidate_conformance,
    seal_execution_substrate_attestation,
)
from valo_kernel.contracts import CanonicalEvent


def run() -> dict[str, str]:
    now = utcnow()
    tenant = "demo-6"
    engine = KernelEngine(tenant)
    engine.append(
        CanonicalEvent(
            event_id="entity-confidential-job",
            event_type=EventType.ENTITY_REGISTERED,
            tenant_id=tenant,
            subject="confidential-job",
            source="kernel",
            payload={
                "entity": {
                    "entity_id": "confidential-job",
                    "entity_type": EntityType.JOB,
                    "tenant_id": tenant,
                    "state": "READY",
                    "provenance": {
                        "source_type": "system",
                        "source_id": "bootstrap",
                        "source_system": "valo-kernel",
                    },
                }
            },
        )
    )
    purpose = Purpose(
        purpose_id="confidential-inference",
        purpose_type="enterprise-inference",
        scope=["confidential-job"],
        basis="enterprise-request",
        permitted_data=["entities:confidential-job"],
        permitted_actions=["RUN"],
        validity=TimeWindow(
            valid_from=now - timedelta(minutes=1),
            valid_until=now + timedelta(hours=1),
        ),
    )
    engine.append(
        CanonicalEvent(
            event_id="purpose-confidential-inference",
            event_type=EventType.PURPOSE_REGISTERED,
            tenant_id=tenant,
            subject=purpose.purpose_id,
            source="kernel",
            effective_at=now,
            payload={"purpose": purpose},
        )
    )

    workload_digest = "b" * 64
    model_digest = "a" * 64
    spec = WorkspaceSpec(
        workspace_id="workspace-confidential-job",
        work_unit_id="work-confidential-job",
        tenant_id=tenant,
        purpose_id=purpose.purpose_id,
        program_ref="valo.enterprise.confidential@1.0.0",
        program_digest=workload_digest,
        selectors=(
            ProjectionSelector(
                collection="entities",
                object_ids=("confidential-job",),
            ),
        ),
        capabilities=(
            WorkspaceCapabilitySpec(
                capability="RUN",
                target_refs=("confidential-job",),
                allowed_effects=("compute",),
            ),
        ),
        allowed_output_kinds=(CandidateKind.EXTERNAL_ACTION,),
        expires_at=now + timedelta(minutes=10),
    )
    requirement = ExecutionSubstrateRequirement(
        allowed_tee_types=("NVIDIA_CC",),
        allowed_measurements=("sha384:trusted-measurement",),
        expected_model_digest=model_digest,
        expected_workload_digest=workload_digest,
    )
    attestation = seal_execution_substrate_attestation(
        attestation_id="quote-1",
        substrate_id="gpu-node-1",
        tee_type="NVIDIA_CC",
        gpu_identity="gpu:0000:01:00.0",
        cc_mode="CONFIDENTIAL_COMPUTE",
        measurement="sha384:trusted-measurement",
        attestation_verifier="verifier:enterprise-tee",
        attestation_evidence_digest="c" * 64,
        attested_at=now,
        valid_until=now + timedelta(minutes=20),
        status=AttestationStatus.VERIFIED,
        confidentiality_protected=True,
        integrity_protected=True,
        isolation_enforced=True,
        model_digest=model_digest,
        workload_digest=workload_digest,
    )
    attested_workspace = compile_attested_governed_workspace(
        engine.state(),
        spec,
        requirement,
        attestation,
        source_event_position=engine.sequence(),
        moment=now,
    )
    action = ProposedAction(
        action_id="run-confidential-job",
        capability="RUN",
        target="confidential-job",
        purpose_id=purpose.purpose_id,
        declared_effects=("compute",),
    )
    candidate = create_candidate_result(
        candidate_id="candidate-confidential-job",
        invocation_id="invocation-confidential-job",
        worker_id="replaceable-worker",
        workspace_id=attested_workspace.workspace.spec.workspace_id,
        workspace_digest=attested_workspace.workspace.workspace_digest,
        output_kind=CandidateKind.EXTERNAL_ACTION,
        proposed_actions=(action,),
    )
    report = evaluate_attested_candidate_conformance(
        attested_workspace,
        candidate,
        engine.state(),
        moment=now + timedelta(seconds=1),
    )
    binding = bind_attested_workspace_execution(
        attested_workspace,
        candidate,
        report,
        action_id=action.action_id,
    )

    assert report.outcome == ConformanceOutcome.PASS
    assert binding.authority_effect == "NO_AUTHORITY_CREATION"
    return {
        "conformance": report.outcome.value,
        "tee_type": binding.tee_type,
        "attestation_digest": binding.substrate_attestation_digest,
        "execution_binding": binding.binding_digest,
    }


def test_demonstrator_6_tee_governed_workspace() -> None:
    result = run()
    assert result["conformance"] == "PASS"
    assert result["tee_type"] == "NVIDIA_CC"


if __name__ == "__main__":
    print(run())
