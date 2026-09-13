from datetime import datetime, timedelta, timezone

import pytest

from valo_workspace import (
    ExposurePolicy,
    GovernedWorkspaceContract,
    ResourceLimits,
    StateAdmissionEvidence,
    StateAdmissionSet,
    WorkspaceDeliveryEvidence,
    bind_workspace_state_admission,
    verify_delivery,
    verify_workspace_state_admission,
)

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)
STATE_DIGEST = "sha256:" + "1" * 64
POLICY_DIGEST = "sha256:" + "2" * 64


def contract() -> GovernedWorkspaceContract:
    return GovernedWorkspaceContract(
        workspace_id="workspace-1",
        purpose="review",
        task_id="task-1",
        worker_id="worker-1",
        governed_state_refs=("state-1",),
        provenance_refs=("prov-1",),
        presented_capabilities=("read",),
        exposure=ExposurePolicy(filesystem_roots=("/safe",), tools=("read",)),
        resources=ResourceLimits(cpu_millis=100, memory_mb=256, wall_time_seconds=30),
        isolation="process",
        valid_from=NOW,
        valid_until=NOW + timedelta(hours=1),
    )


def admission() -> StateAdmissionSet:
    return StateAdmissionSet(
        admission_set_id="set-1",
        issuer_id="issuer-1",
        issued_at=NOW,
        entries=(
            StateAdmissionEvidence(
                admission_id="admission-1",
                state_ref="state-1",
                state_digest=STATE_DIGEST,
                decision="ADMITTED",
                provenance_refs=("prov-1",),
                authority_refs=("authority-1",),
                admission_policy_digest=POLICY_DIGEST,
                issuer_id="issuer-1",
                evaluated_at=NOW,
                valid_until=NOW + timedelta(minutes=30),
            ),
        ),
    )


def test_admitted_state_binds_to_workspace_without_authority():
    result = verify_workspace_state_admission(contract(), admission(), at=NOW)
    assert result.conformant
    binding = bind_workspace_state_admission(contract(), admission(), bound_at=NOW)
    assert binding.governed_state_refs == ("state-1",)
    assert binding.valid_until == NOW + timedelta(minutes=30)


def test_delivery_rejects_scope_widening():
    evidence = WorkspaceDeliveryEvidence(
        workspace_id="workspace-1",
        provider_id="provider-1",
        runtime_id="runtime-1",
        runtime_digest="sha256:" + "3" * 64,
        realized_isolation="process",
        filesystem_roots=("/safe", "/secret"),
        delivered_at=NOW,
        expires_at=NOW + timedelta(minutes=20),
    )
    result = verify_delivery(contract(), evidence, now=NOW)
    assert not result.conformant
    assert "filesystem_scope_widened" in result.violations


def test_non_admitted_state_fails_closed():
    rejected = admission().model_copy(
        update={
            "entries": (
                admission().entries[0].model_copy(update={"decision": "CANDIDATE"}),
            ),
        }
    )
    result = verify_workspace_state_admission(contract(), rejected, at=NOW)
    assert not result.conformant
    with pytest.raises(ValueError, match="state_not_admitted"):
        bind_workspace_state_admission(contract(), rejected, bound_at=NOW)


def test_reasoning_telemetry_cannot_be_authority():
    payload = admission().entries[0].model_dump()
    payload["authority_refs"] = ("reasoning:confidence",)
    with pytest.raises(ValueError, match="non-authoritative"):
        StateAdmissionEvidence(**payload)
