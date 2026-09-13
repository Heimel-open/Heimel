from __future__ import annotations

from ..contracts.model_portability import (
    HardwareCapabilityProfile,
    ModelPortabilityAssessment,
    PortabilityOutcome,
    PortableModelArtifact,
    SemanticEquivalenceEvidence,
)
from .errors import FailClosedError


def seal_portable_model_artifact(**values: object) -> PortableModelArtifact:
    provisional = PortableModelArtifact(**values)
    return provisional.model_copy(update={"artifact_digest": provisional.computed_digest})


def seal_hardware_capability_profile(**values: object) -> HardwareCapabilityProfile:
    provisional = HardwareCapabilityProfile(**values)
    return provisional.model_copy(
        update={"capability_digest": provisional.computed_digest}
    )


def seal_semantic_equivalence_evidence(
    **values: object,
) -> SemanticEquivalenceEvidence:
    provisional = SemanticEquivalenceEvidence(**values)
    return provisional.model_copy(update={"evidence_digest": provisional.computed_digest})


def assess_model_portability(
    model: PortableModelArtifact,
    capability: HardwareCapabilityProfile,
    *,
    equivalence_evidence: SemanticEquivalenceEvidence | None = None,
) -> ModelPortabilityAssessment:
    if model.artifact_digest != model.computed_digest:
        raise FailClosedError("portable model artifact is unsealed or tampered")
    if capability.capability_digest != capability.computed_digest:
        raise FailClosedError("hardware capability profile is unsealed or tampered")
    if (
        equivalence_evidence is not None
        and equivalence_evidence.evidence_digest != equivalence_evidence.computed_digest
    ):
        raise FailClosedError("semantic equivalence evidence is unsealed or tampered")

    reasons: list[str] = []
    deny = False

    if model.format_id not in capability.supported_formats:
        reasons.append("PORTABLE_FORMAT_UNSUPPORTED")
        deny = True

    if capability.available_memory_bytes < model.minimum_memory_bytes:
        reasons.append("INSUFFICIENT_MEMORY")
        deny = True

    missing_operators = tuple(
        sorted(set(model.required_operators) - set(capability.supported_operators))
    )
    if missing_operators:
        if capability.cpu_fallback_available:
            reasons.append("OPERATOR_FALLBACK_REQUIRED")
        else:
            reasons.append("REQUIRED_OPERATOR_UNSUPPORTED")
            deny = True

    selected_precision = next(
        (
            precision
            for precision in model.allowed_precisions
            if precision in capability.supported_precisions
        ),
        None,
    )
    if selected_precision is None:
        reasons.append("NO_ACCEPTABLE_PRECISION")
        deny = True

    evidence_digest: str | None = None
    if equivalence_evidence is None:
        reasons.append("SEMANTIC_EQUIVALENCE_NOT_ESTABLISHED")
        deny = True
    else:
        evidence_digest = equivalence_evidence.evidence_digest
        if equivalence_evidence.portable_model_digest != model.artifact_digest:
            reasons.append("SEMANTIC_EVIDENCE_MODEL_BINDING")
            deny = True
        if equivalence_evidence.reference_backend_id != model.reference_backend_id:
            reasons.append("SEMANTIC_EVIDENCE_REFERENCE_BINDING")
            deny = True
        if equivalence_evidence.candidate_backend_id != capability.backend_id:
            reasons.append("SEMANTIC_EVIDENCE_BACKEND_BINDING")
            deny = True
        if not equivalence_evidence.passed:
            reasons.append("SEMANTIC_EQUIVALENCE_FAILED")
            deny = True

    if deny:
        outcome = PortabilityOutcome.DENY
    elif reasons:
        outcome = PortabilityOutcome.DEGRADED
    else:
        outcome = PortabilityOutcome.PASS

    provisional = ModelPortabilityAssessment(
        assessment_id=f"model-portability:{model.model_id}:{capability.backend_id}",
        portable_model_digest=model.artifact_digest,
        capability_digest=capability.capability_digest,
        backend_id=capability.backend_id,
        outcome=outcome,
        selected_precision=selected_precision,
        missing_operators=missing_operators,
        reasons=tuple(reasons),
        semantic_equivalence_evidence_digest=evidence_digest,
    )
    return provisional.model_copy(
        update={"assessment_digest": provisional.computed_digest}
    )
