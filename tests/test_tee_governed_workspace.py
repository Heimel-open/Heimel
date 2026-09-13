from __future__ import annotations

from datetime import timedelta

import pytest

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
from valo_kernel.kernel.errors import FailClosedError

MODEL_DIGEST = "a" * 64
WORKLOAD_DIGEST = "b" * 64
MEASUREMENT = "sha384:trusted-measurement"


def _engine_and_spec(now):
    tenant = "tenant-tee"
    engine = KernelEngine(tenant)
    engine.append(
        CanonicalEvent(
            event_id="entity-job-tee",
            event_type=EventType.ENTITY_REGISTERED,
            tenant_id=tenant,
            subject="job-tee",
            source="kernel",
            payload={
                "entity": {
                    "entity_id": "job-tee",
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
        purpose_id="purpose-tee",
        purpose_type="confidential-job",
        scope=["job-tee"],
        basis="enterprise-request",
        permitted_data=["entities:job-tee"],
        permitted_actions=["RUN"],
        validity=TimeWindow(
            valid_from=now - timedelta(minutes=1),
            valid_until=now + timedelta(hours=1),
        ),
    )
    engine.append(
        CanonicalEvent(
            event_id="purpose-tee",
            event_type=EventType.PURPOSE_REGISTERED,
            tenant_id=tenant,
            subject=purpose.purpose_id,
            source="kernel",
            effective_at=now,
            payload={"purpose": purpose},
        )
    )
    spec = WorkspaceSpec(
        workspace_id="workspace-tee",
        work_unit_id="work-unit-tee",
        tenant_id=tenant,
        purpose_id=purpose.purpose_id,
        program_ref="valo.enterprise.confidential@1.0.0",
        program_digest=WORKLOAD_DIGEST,
        selectors=(
            ProjectionSelector(collection="entities", object_ids=("job-tee",)),
        ),
        capabilities=(
            WorkspaceCapabilitySpec(
                capability="RUN",
                target_refs=("job-tee",),
                allowed_effects=("compute",),
            ),
        ),
        allowed_output_kinds=(CandidateKind.EXTERNAL_ACTION,),
        expires_at=now + timedelta(minutes=15),
    )
    return engine, spec


def _requirement(*, max_age: int = 300):
    return ExecutionSubstrateRequirement(
        allowed_tee_types=("NVIDIA_CC",),
        allowed_measurements=(MEASUREMENT,),
        max_attestation_age_seconds=max_age,
        expected_model_digest=MODEL_DIGEST,
        expected_workload_digest=WORKLOAD_DIGEST,
    )


def _attestation(now, **updates):
    values = {
        "attestation_id": "attestation-1",
        "substrate_id": "gpu-node-1",
        "tee_type": "NVIDIA_CC",
        "gpu_identity": "gpu:0000:01:00.0",
        "cc_mode": "CONFIDENTIAL_COMPUTE",
        "measurement": MEASUREMENT,
        "attestation_verifier": "verifier:enterprise-tee",
        "attestation_evidence_digest": "c" * 64,
        "attested_at": now,
        "valid_until": now + timedelta(minutes=30),
        "status": AttestationStatus.VERIFIED,
        "confidentiality_protected": True,
        "integrity_protected": True,
        "isolation_enforced": True,
        "model_digest": MODEL_DIGEST,
        "workload_digest": WORKLOAD_DIGEST,
    }
    values.update(updates)
    return seal_execution_substrate_attestation(**values)


def _candidate(attested_workspace):
    workspace = attested_workspace.workspace
    action = ProposedAction(
        action_id="run-1",
        capability="RUN",
        target="job-tee",
        purpose_id="purpose-tee",
        declared_effects=("compute",),
    )
    return create_candidate_result(
        candidate_id="candidate-tee",
        invocation_id="invocation-tee",
        worker_id="replaceable-worker",
        workspace_id=workspace.spec.workspace_id,
        workspace_digest=workspace.workspace_digest,
        output_kind=CandidateKind.EXTERNAL_ACTION,
        proposed_actions=(action,),
    )


def test_verified_tee_is_bound_to_governed_workspace_and_execution() -> None:
    now = utcnow()
    engine, spec = _engine_and_spec(now)
    attestation = _attestation(now)
    first = compile_attested_governed_workspace(
        engine.state(),
        spec,
        _requirement(),
        attestation,
        source_event_position=engine.sequence(),
        moment=now,
    )
    second = compile_attested_governed_workspace(
        engine.state(),
        spec,
        _requirement(),
        attestation,
        source_event_position=engine.sequence(),
        moment=now,
    )

    assert first == second
    assert first.attested_workspace_digest == first.computed_digest
    assert first.authority_effect == "NO_AUTHORITY_CREATION"
    assert first.can_issue_clearance is False
    assert first.substrate_attestation.attestation_digest == attestation.computed_digest

    candidate = _candidate(first)
    report = evaluate_attested_candidate_conformance(
        first,
        candidate,
        engine.state(),
        moment=now + timedelta(seconds=1),
    )
    assert report.outcome == ConformanceOutcome.PASS

    binding = bind_attested_workspace_execution(
        first,
        candidate,
        report,
        action_id="run-1",
    )
    assert binding.binding_digest == binding.computed_digest
    assert binding.substrate_attestation_digest == attestation.attestation_digest
    assert binding.tee_type == "NVIDIA_CC"
    assert binding.gpu_identity == "gpu:0000:01:00.0"
    assert binding.cc_mode == "CONFIDENTIAL_COMPUTE"
    assert binding.measurement == MEASUREMENT
    assert binding.model_digest == MODEL_DIGEST
    assert binding.workload_digest == WORKLOAD_DIGEST
    assert binding.authority_effect == "NO_AUTHORITY_CREATION"
    assert binding.can_issue_clearance is False


def test_missing_attestation_fails_closed() -> None:
    now = utcnow()
    engine, spec = _engine_and_spec(now)
    with pytest.raises(FailClosedError, match="requires verified substrate attestation"):
        compile_attested_governed_workspace(
            engine.state(),
            spec,
            _requirement(),
            None,
            source_event_position=engine.sequence(),
            moment=now,
        )


@pytest.mark.parametrize(
    ("updates", "code"),
    [
        ({"status": AttestationStatus.REVOKED}, "TEE_ATTESTATION_UNVERIFIED"),
        ({"status": AttestationStatus.INVALID}, "TEE_ATTESTATION_UNVERIFIED"),
        ({"tee_type": "OTHER_TEE"}, "TEE_TYPE_MISMATCH"),
        ({"measurement": "sha384:unexpected"}, "TEE_MEASUREMENT_MISMATCH"),
        ({"confidentiality_protected": False}, "TEE_CONFIDENTIALITY_REQUIRED"),
        ({"integrity_protected": False}, "TEE_INTEGRITY_REQUIRED"),
        ({"isolation_enforced": False}, "TEE_ISOLATION_REQUIRED"),
        ({"model_digest": "d" * 64}, "TEE_MODEL_MISMATCH"),
        ({"workload_digest": "e" * 64}, "TEE_WORKLOAD_MISMATCH"),
    ],
)
def test_invalid_or_mismatched_attestation_fails_closed(updates, code) -> None:
    now = utcnow()
    engine, spec = _engine_and_spec(now)
    with pytest.raises(FailClosedError, match=code):
        compile_attested_governed_workspace(
            engine.state(),
            spec,
            _requirement(),
            _attestation(now, **updates),
            source_event_position=engine.sequence(),
            moment=now,
        )


def test_workspace_cannot_outlive_tee_attestation() -> None:
    now = utcnow()
    engine, spec = _engine_and_spec(now)
    attestation = _attestation(now, valid_until=now + timedelta(minutes=10))
    with pytest.raises(FailClosedError, match="TEE_ATTESTATION_WINDOW"):
        compile_attested_governed_workspace(
            engine.state(),
            spec,
            _requirement(),
            attestation,
            source_event_position=engine.sequence(),
            moment=now,
        )


def test_stale_attestation_defers_and_produces_no_execution_binding() -> None:
    now = utcnow()
    engine, spec = _engine_and_spec(now)
    workspace = compile_attested_governed_workspace(
        engine.state(),
        spec,
        _requirement(max_age=60),
        _attestation(now),
        source_event_position=engine.sequence(),
        moment=now,
    )
    candidate = _candidate(workspace)
    report = evaluate_attested_candidate_conformance(
        workspace,
        candidate,
        engine.state(),
        moment=now + timedelta(seconds=61),
    )

    assert report.outcome == ConformanceOutcome.DEFER
    assert "TEE_ATTESTATION_STALE" in {item.code for item in report.mismatches}
    with pytest.raises(FailClosedError, match="only PASS attested conformance"):
        bind_attested_workspace_execution(
            workspace,
            candidate,
            report,
            action_id="run-1",
        )


def test_tampered_attestation_halts_before_execution_binding() -> None:
    now = utcnow()
    engine, spec = _engine_and_spec(now)
    workspace = compile_attested_governed_workspace(
        engine.state(),
        spec,
        _requirement(),
        _attestation(now),
        source_event_position=engine.sequence(),
        moment=now,
    )
    tampered_attestation = workspace.substrate_attestation.model_copy(
        update={"attestation_digest": "0" * 64}
    )
    tampered_workspace = workspace.model_copy(
        update={"substrate_attestation": tampered_attestation}
    )
    candidate = _candidate(workspace)
    report = evaluate_attested_candidate_conformance(
        tampered_workspace,
        candidate,
        engine.state(),
        moment=now + timedelta(seconds=1),
    )

    assert report.outcome == ConformanceOutcome.HALT
    codes = {item.code for item in report.mismatches}
    assert "TEE_ATTESTATION_TAMPER" in codes
    assert "ATTESTED_WORKSPACE_TAMPER" in codes
