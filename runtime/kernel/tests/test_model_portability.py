from __future__ import annotations

import pytest
from pydantic import ValidationError

from valo_kernel.contracts.model_portability import (
    BackendDeploymentArtifact,
    PortabilityOutcome,
)
from valo_kernel.kernel.model_portability import (
    assess_model_portability,
    seal_hardware_capability_profile,
    seal_portable_model_artifact,
    seal_semantic_equivalence_evidence,
)


def _model():
    return seal_portable_model_artifact(
        model_id="personal-model-1",
        format_id="portable-ir.v1",
        graph_digest="a" * 64,
        weights_digest="b" * 64,
        metadata_digest="c" * 64,
        semantic_contract_digest="d" * 64,
        required_operators=("attention", "matmul", "norm"),
        allowed_precisions=("BF16", "FP16", "INT8"),
        minimum_memory_bytes=8_000_000_000,
        reference_backend_id="cpu-reference",
    )


def _capability(**updates):
    values = {
        "backend_id": "edge-npu-a",
        "hardware_class": "NPU",
        "supported_formats": ("portable-ir.v1",),
        "supported_operators": ("attention", "matmul", "norm"),
        "supported_precisions": ("FP16", "INT8"),
        "available_memory_bytes": 16_000_000_000,
        "trust_root_ids": ("trust-root-a",),
        "cpu_fallback_available": False,
    }
    values.update(updates)
    return seal_hardware_capability_profile(**values)


def _evidence(model, capability, **updates):
    values = {
        "evidence_id": "equivalence-1",
        "portable_model_digest": model.artifact_digest,
        "reference_backend_id": model.reference_backend_id,
        "candidate_backend_id": capability.backend_id,
        "test_suite_digest": "e" * 64,
        "tolerance_profile_digest": "f" * 64,
        "passed": True,
    }
    values.update(updates)
    return seal_semantic_equivalence_evidence(**values)


def test_supported_backend_passes_only_with_semantic_equivalence() -> None:
    model = _model()
    capability = _capability()
    evidence = _evidence(model, capability)

    assessment = assess_model_portability(
        model,
        capability,
        equivalence_evidence=evidence,
    )

    assert assessment.outcome is PortabilityOutcome.PASS
    assert assessment.selected_precision == "FP16"
    assert assessment.reasons == ()
    assert assessment.semantic_equivalence_evidence_digest == evidence.evidence_digest
    assert assessment.can_issue_clearance is False


def test_missing_semantic_equivalence_fails_closed() -> None:
    assessment = assess_model_portability(_model(), _capability())

    assert assessment.outcome is PortabilityOutcome.DENY
    assert "SEMANTIC_EQUIVALENCE_NOT_ESTABLISHED" in assessment.reasons


def test_wrong_backend_semantic_evidence_fails_closed() -> None:
    model = _model()
    capability = _capability()
    evidence = _evidence(model, capability, candidate_backend_id="other-backend")

    assessment = assess_model_portability(
        model,
        capability,
        equivalence_evidence=evidence,
    )

    assert assessment.outcome is PortabilityOutcome.DENY
    assert "SEMANTIC_EVIDENCE_BACKEND_BINDING" in assessment.reasons


def test_operator_gap_can_degrade_with_explicit_cpu_fallback() -> None:
    model = _model()
    capability = _capability(
        supported_operators=("attention", "matmul"),
        cpu_fallback_available=True,
    )
    evidence = _evidence(model, capability)

    assessment = assess_model_portability(
        model,
        capability,
        equivalence_evidence=evidence,
    )

    assert assessment.outcome is PortabilityOutcome.DEGRADED
    assert assessment.missing_operators == ("norm",)
    assert assessment.reasons == ("OPERATOR_FALLBACK_REQUIRED",)


def test_operator_gap_without_fallback_is_denied() -> None:
    model = _model()
    capability = _capability(supported_operators=("attention", "matmul"))
    evidence = _evidence(model, capability)

    assessment = assess_model_portability(
        model,
        capability,
        equivalence_evidence=evidence,
    )

    assert assessment.outcome is PortabilityOutcome.DENY
    assert "REQUIRED_OPERATOR_UNSUPPORTED" in assessment.reasons


def test_portable_source_not_specialized_binary_is_canonical() -> None:
    model = _model()
    deployment = BackendDeploymentArtifact(
        deployment_id="deploy-edge-npu-a",
        portable_model_digest=model.artifact_digest,
        backend_id="edge-npu-a",
        deployment_digest="1" * 64,
    )

    assert deployment.specialized is True
    assert deployment.rebuildable_from_portable_source is True
    assert deployment.portable_source_is_canonical is True
    assert deployment.authoritative_state_role == "NONE"

    with pytest.raises(ValidationError):
        BackendDeploymentArtifact(
            deployment_id="deploy-edge-npu-a",
            portable_model_digest=model.artifact_digest,
            backend_id="edge-npu-a",
            deployment_digest="1" * 64,
            portable_source_is_canonical=False,
        )


def test_hardware_profile_cannot_create_authority() -> None:
    with pytest.raises(ValidationError):
        _capability(can_issue_clearance=True)
