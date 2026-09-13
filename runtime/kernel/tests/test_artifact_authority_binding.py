from __future__ import annotations

import pytest
from pydantic import ValidationError

from valo_kernel import ArtifactContextBinding, CandidateKind, CandidateResult


def _binding(
    *,
    workspace_id: str = "workspace-1",
    workspace_digest: str = "b" * 64,
    invocation_id: str = "invocation-1",
    candidate_id: str = "candidate-1",
    worker_id: str = "worker-1",
) -> ArtifactContextBinding:
    provisional = ArtifactContextBinding(
        artifact_ref="artifact:reasoning:1",
        artifact_digest="a" * 64,
        workspace_id=workspace_id,
        workspace_digest=workspace_digest,
        invocation_id=invocation_id,
        candidate_id=candidate_id,
        worker_id=worker_id,
        session_id="session-1",
        continuation_nonce="nonce-1",
        predecessor_digest="c" * 64,
        producer_model_ref="provider:model-1",
    )
    return provisional.model_copy(
        update={"binding_digest": provisional.computed_digest}
    )


def _candidate(binding: ArtifactContextBinding, **updates: str) -> CandidateResult:
    values = {
        "candidate_id": "candidate-1",
        "invocation_id": "invocation-1",
        "worker_id": "worker-1",
        "workspace_id": "workspace-1",
        "workspace_digest": "b" * 64,
        "output_kind": CandidateKind.ARTIFACT,
        "artifact_refs": (binding.artifact_ref,),
        "artifact_bindings": (binding,),
    }
    values.update(updates)
    provisional = CandidateResult(**values)
    return provisional.model_copy(
        update={"candidate_digest": provisional.computed_digest}
    )


def test_artifact_binding_is_context_bound_and_non_authoritative() -> None:
    binding = _binding()
    candidate = _candidate(binding)

    assert candidate.artifact_bindings == (binding,)
    assert binding.authority_effect == "NO_AUTHORITY_CREATION"
    assert binding.can_issue_clearance is False
    assert binding.single_use_required is True


def test_unbound_artifact_ref_fails_closed() -> None:
    with pytest.raises(ValidationError, match="explicit context bindings"):
        CandidateResult(
            candidate_id="candidate-1",
            invocation_id="invocation-1",
            worker_id="worker-1",
            workspace_id="workspace-1",
            workspace_digest="b" * 64,
            output_kind=CandidateKind.ARTIFACT,
            artifact_refs=("artifact:reasoning:1",),
        )


def test_artifact_replay_into_another_invocation_fails_closed() -> None:
    binding = _binding()

    with pytest.raises(ValidationError, match="another invocation"):
        _candidate(binding, invocation_id="invocation-2")


def test_artifact_replay_into_another_workspace_fails_closed() -> None:
    binding = _binding()

    with pytest.raises(ValidationError, match="another workspace"):
        _candidate(
            binding,
            workspace_id="workspace-2",
            workspace_digest="d" * 64,
        )


def test_tampered_artifact_binding_fails_closed() -> None:
    binding = _binding()
    tampered = binding.model_copy(update={"producer_model_ref": "provider:model-2"})

    with pytest.raises(ValidationError, match="binding digest mismatch"):
        _candidate(tampered)
