from __future__ import annotations

from datetime import datetime

from ..contracts.execution_substrate import (
    AttestationStatus,
    AttestedConformanceReport,
    AttestedGovernedWorkspaceEnvelope,
    AttestedWorkspaceExecutionBinding,
    ExecutionSubstrateAttestation,
    ExecutionSubstrateRequirement,
)
from ..contracts.workspace import (
    CandidateResult,
    ConformanceMismatch,
    ConformanceOutcome,
    WorkspaceSpec,
)
from ..world.state import WorldState
from .errors import FailClosedError
from .workspace import (
    bind_workspace_execution,
    compile_governed_workspace,
    evaluate_candidate_conformance,
)

_OUTCOME_PRIORITY = {
    ConformanceOutcome.PASS: 0,
    ConformanceOutcome.REDO: 10,
    ConformanceOutcome.DEFER: 20,
    ConformanceOutcome.STEP_UP: 25,
    ConformanceOutcome.DENY: 30,
    ConformanceOutcome.HALT: 40,
}


def _promote(
    current: ConformanceOutcome,
    proposed: ConformanceOutcome,
) -> ConformanceOutcome:
    if _OUTCOME_PRIORITY[proposed] > _OUTCOME_PRIORITY[current]:
        return proposed
    return current


def _substrate_mismatches(
    requirement: ExecutionSubstrateRequirement,
    attestation: ExecutionSubstrateAttestation,
    *,
    moment: datetime,
    workspace_expires_at: datetime,
) -> tuple[tuple[ConformanceMismatch, ...], ConformanceOutcome]:
    mismatches: list[ConformanceMismatch] = []
    severity = ConformanceOutcome.PASS

    def add(code: str, detail: str, outcome: ConformanceOutcome) -> None:
        nonlocal severity
        mismatches.append(ConformanceMismatch(code=code, detail=detail))
        severity = _promote(severity, outcome)

    if attestation.attestation_digest != attestation.computed_digest:
        add(
            "TEE_ATTESTATION_TAMPER",
            "execution substrate attestation is unsealed",
            ConformanceOutcome.HALT,
        )
    if attestation.status != AttestationStatus.VERIFIED:
        add(
            "TEE_ATTESTATION_UNVERIFIED",
            f"attestation status is {attestation.status.value}",
            ConformanceOutcome.HALT,
        )
    if attestation.tee_type not in requirement.allowed_tee_types:
        add(
            "TEE_TYPE_MISMATCH",
            "attested TEE type is outside workspace requirement",
            ConformanceOutcome.HALT,
        )
    if (
        requirement.allowed_measurements
        and attestation.measurement not in requirement.allowed_measurements
    ):
        add(
            "TEE_MEASUREMENT_MISMATCH",
            "attested measurement is outside workspace requirement",
            ConformanceOutcome.HALT,
        )
    if requirement.require_confidentiality and not attestation.confidentiality_protected:
        add(
            "TEE_CONFIDENTIALITY_REQUIRED",
            "confidentiality protection is not attested",
            ConformanceOutcome.HALT,
        )
    if requirement.require_integrity and not attestation.integrity_protected:
        add(
            "TEE_INTEGRITY_REQUIRED",
            "integrity protection is not attested",
            ConformanceOutcome.HALT,
        )
    if requirement.require_isolation and not attestation.isolation_enforced:
        add(
            "TEE_ISOLATION_REQUIRED",
            "execution isolation is not attested",
            ConformanceOutcome.HALT,
        )
    if (
        requirement.expected_model_digest is not None
        and attestation.model_digest != requirement.expected_model_digest
    ):
        add(
            "TEE_MODEL_MISMATCH",
            "attested model digest differs from workspace requirement",
            ConformanceOutcome.HALT,
        )
    if (
        requirement.expected_workload_digest is not None
        and attestation.workload_digest != requirement.expected_workload_digest
    ):
        add(
            "TEE_WORKLOAD_MISMATCH",
            "attested workload digest differs from workspace requirement",
            ConformanceOutcome.HALT,
        )
    if moment < attestation.attested_at:
        add(
            "TEE_ATTESTATION_FUTURE",
            "attestation timestamp is later than evaluation time",
            ConformanceOutcome.HALT,
        )
    elif moment >= attestation.valid_until:
        add(
            "TEE_ATTESTATION_EXPIRED",
            "execution substrate attestation has expired",
            ConformanceOutcome.DEFER,
        )
    elif (
        moment - attestation.attested_at
    ).total_seconds() > requirement.max_attestation_age_seconds:
        add(
            "TEE_ATTESTATION_STALE",
            "execution substrate attestation is too old",
            ConformanceOutcome.DEFER,
        )
    if attestation.valid_until < workspace_expires_at:
        add(
            "TEE_ATTESTATION_WINDOW",
            "workspace outlives the attested execution substrate",
            ConformanceOutcome.DEFER,
        )

    return tuple(mismatches), severity


def compile_attested_governed_workspace(
    state: WorldState,
    spec: WorkspaceSpec,
    requirement: ExecutionSubstrateRequirement,
    attestation: ExecutionSubstrateAttestation | None,
    *,
    source_event_position: int,
    moment: datetime,
) -> AttestedGovernedWorkspaceEnvelope:
    if attestation is None:
        raise FailClosedError("TEE workspace requires verified substrate attestation")

    workspace = compile_governed_workspace(
        state,
        spec,
        source_event_position=source_event_position,
        moment=moment,
    )
    mismatches, _ = _substrate_mismatches(
        requirement,
        attestation,
        moment=moment,
        workspace_expires_at=workspace.spec.expires_at,
    )
    if mismatches:
        codes = ",".join(item.code for item in mismatches)
        raise FailClosedError(f"TEE workspace substrate rejected: {codes}")

    provisional = AttestedGovernedWorkspaceEnvelope(
        workspace=workspace,
        substrate_requirement=requirement,
        substrate_attestation=attestation,
    )
    return provisional.model_copy(
        update={"attested_workspace_digest": provisional.computed_digest}
    )


def evaluate_attested_candidate_conformance(
    attested_workspace: AttestedGovernedWorkspaceEnvelope,
    candidate: CandidateResult,
    current_state: WorldState,
    *,
    moment: datetime,
) -> AttestedConformanceReport:
    base_report = evaluate_candidate_conformance(
        attested_workspace.workspace,
        candidate,
        current_state,
        moment=moment,
    )
    substrate_mismatches, substrate_outcome = _substrate_mismatches(
        attested_workspace.substrate_requirement,
        attested_workspace.substrate_attestation,
        moment=moment,
        workspace_expires_at=attested_workspace.workspace.spec.expires_at,
    )
    wrapper_mismatches: tuple[ConformanceMismatch, ...] = ()
    wrapper_outcome = ConformanceOutcome.PASS
    if attested_workspace.attested_workspace_digest != attested_workspace.computed_digest:
        wrapper_mismatches = (
            ConformanceMismatch(
                code="ATTESTED_WORKSPACE_TAMPER",
                detail="attested governed workspace is unsealed",
            ),
        )
        wrapper_outcome = ConformanceOutcome.HALT

    outcome = _promote(base_report.outcome, substrate_outcome)
    outcome = _promote(outcome, wrapper_outcome)
    mismatches = base_report.mismatches + substrate_mismatches + wrapper_mismatches
    provisional = AttestedConformanceReport(
        base_report=base_report,
        attested_workspace_digest=attested_workspace.attested_workspace_digest,
        substrate_attestation_digest=(
            attested_workspace.substrate_attestation.attestation_digest
        ),
        outcome=outcome,
        mismatches=mismatches,
        evaluated_at=base_report.evaluated_at,
    )
    return provisional.model_copy(update={"report_digest": provisional.computed_digest})


def bind_attested_workspace_execution(
    attested_workspace: AttestedGovernedWorkspaceEnvelope,
    candidate: CandidateResult,
    report: AttestedConformanceReport,
    *,
    action_id: str,
) -> AttestedWorkspaceExecutionBinding:
    if report.outcome != ConformanceOutcome.PASS:
        raise FailClosedError(
            "only PASS attested conformance can produce an execution binding"
        )
    if attested_workspace.attested_workspace_digest != attested_workspace.computed_digest:
        raise FailClosedError("attested governed workspace is unsealed")
    attestation = attested_workspace.substrate_attestation
    if attestation.attestation_digest != attestation.computed_digest:
        raise FailClosedError("execution substrate attestation is unsealed")
    if report.report_digest != report.computed_digest:
        raise FailClosedError("attested conformance report is unsealed")
    if report.attested_workspace_digest != attested_workspace.attested_workspace_digest:
        raise FailClosedError("attested workspace report binding mismatch")
    if report.substrate_attestation_digest != attestation.attestation_digest:
        raise FailClosedError("substrate attestation report binding mismatch")

    base_binding = bind_workspace_execution(
        attested_workspace.workspace,
        candidate,
        report.base_report,
        action_id=action_id,
    )
    provisional = AttestedWorkspaceExecutionBinding(
        base_binding=base_binding,
        attested_workspace_digest=attested_workspace.attested_workspace_digest,
        substrate_attestation_digest=attestation.attestation_digest,
        substrate_id=attestation.substrate_id,
        tee_type=attestation.tee_type,
        gpu_identity=attestation.gpu_identity,
        cc_mode=attestation.cc_mode,
        measurement=attestation.measurement,
        attestation_verifier=attestation.attestation_verifier,
        attestation_evidence_digest=attestation.attestation_evidence_digest,
        attested_at=attestation.attested_at,
        attestation_valid_until=attestation.valid_until,
        model_digest=attestation.model_digest,
        workload_digest=attestation.workload_digest,
    )
    return provisional.model_copy(update={"binding_digest": provisional.computed_digest})
