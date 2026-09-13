"""Tests for exact Verification Factory and Harness intake."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from vaig.ensemble import DistrustLevel
from vaig.evidence_intake import (
    ClaimAdmissibilityBinding,
    ClaimDisposition,
    ClaimMateriality,
    CriterionKind,
    CriterionVerificationBinding,
    EvidenceIntakeRequest,
    EvidenceIntakeState,
    EvidencePackageBinding,
    VersionedArtifactRef,
    WorkflowVerificationBinding,
    assess_evidence_intake,
)
from vaig.orchestrator import VAIGOrchestrator


NOW = datetime(2026, 7, 29, 16, 30, tzinfo=timezone.utc)


def digest(character: str) -> str:
    return "sha256:" + character * 64


def ref(identifier: str, character: str = "a") -> VersionedArtifactRef:
    return VersionedArtifactRef(
        artifact_id=identifier,
        version="v1",
        reference=f"ref:{identifier}:v1",
        digest=digest(character),
    )


def record(
    disposition: ClaimDisposition = ClaimDisposition.SUPPORTED,
    materiality: ClaimMateriality = ClaimMateriality.HIGH,
    permissible_uses=("approve_payment",),
    prohibited_uses=(),
    unresolved_conflicts=(),
    limitations=(),
    invalidated=False,
) -> ClaimAdmissibilityBinding:
    return ClaimAdmissibilityBinding(
        admissibility_ref=ref("admissibility-1", "b"),
        case_id="case-1",
        claim_id="claim-1",
        disposition=disposition,
        materiality=materiality,
        permissible_uses=tuple(permissible_uses),
        prohibited_uses=tuple(prohibited_uses),
        unresolved_conflicts=tuple(unresolved_conflicts),
        limitations=tuple(limitations),
        policy_ref=ref("policy-1", "c"),
        decided_at=NOW - timedelta(minutes=5),
        invalidated_at=(NOW - timedelta(minutes=1) if invalidated else None),
        invalidation_ref=(ref("invalidation-1", "d") if invalidated else None),
    )


def package(
    *,
    package_digest=digest("e"),
    created_at=NOW - timedelta(minutes=10),
    permissible_uses=("approve_payment",),
    prohibited_uses=(),
    unresolved_questions=(),
    contradictions=(),
    invalidated=False,
) -> EvidencePackageBinding:
    return EvidencePackageBinding(
        package_id="package-1",
        case_id="case-1",
        package_version="v1",
        package_digest=package_digest,
        admissibility_refs=(ref("admissibility-1", "b"),),
        unresolved_questions=tuple(unresolved_questions),
        contradictions=tuple(contradictions),
        permissible_uses=tuple(permissible_uses),
        prohibited_uses=tuple(prohibited_uses),
        created_at=created_at,
        invalidated_at=(NOW - timedelta(minutes=1) if invalidated else None),
        invalidation_ref=(ref("package-invalidation", "f") if invalidated else None),
    )


def request(**overrides) -> EvidenceIntakeRequest:
    values = {
        "required": True,
        "intended_use": "approve_payment",
        "expected_case_id": "case-1",
        "expected_package_id": "package-1",
        "expected_package_version": "v1",
        "expected_package_digest": digest("e"),
        "max_package_age_seconds": 3600,
    }
    values.update(overrides)
    return EvidenceIntakeRequest(**values)


def criterion(
    criterion_id: str = "criterion-1",
    kind: CriterionKind = CriterionKind.DETERMINISTIC,
    blocking: bool = True,
    status: str = "SUCCEEDED",
) -> CriterionVerificationBinding:
    return CriterionVerificationBinding(
        criterion_id=criterion_id,
        binding_fingerprint=digest("1"),
        kind=kind,
        blocking=blocking,
        status=status,
        verifier_id="verifier-1",
        verifier_version="v1",
        evidence_digest=digest("2"),
    )


def workflow(
    *,
    accepted=True,
    criteria=None,
    unresolved_criteria=(),
    invalidated=False,
) -> WorkflowVerificationBinding:
    return WorkflowVerificationBinding(
        bundle_fingerprint=digest("3"),
        workflow_fingerprint=digest("4"),
        node_fingerprint=digest("5"),
        workflow_state_fingerprint=digest("6"),
        accepted=accepted,
        criteria=tuple(criteria if criteria is not None else (criterion(),)),
        unresolved_criteria=tuple(unresolved_criteria),
        invalidated_at=(NOW - timedelta(minutes=1) if invalidated else None),
        invalidation_ref=(ref("workflow-invalidation", "7") if invalidated else None),
    )


def test_not_required_without_artifacts_is_explicit():
    assessment = assess_evidence_intake(
        EvidenceIntakeRequest(required=False, intended_use=""),
        now=NOW,
    )

    assert assessment.state is EvidenceIntakeState.NOT_REQUIRED
    assert assessment.blocks_consequential_action is False
    assert assessment.evidence_valid is True
    assert assessment.claims_substantiated is True


def test_missing_required_package_fails_closed():
    assessment = assess_evidence_intake(request(), now=NOW)

    assert assessment.state is EvidenceIntakeState.MISSING
    assert assessment.blocks_consequential_action is True
    assert assessment.evidence_valid is False


def test_exact_supported_package_is_valid():
    assessment = assess_evidence_intake(
        request(),
        package=package(),
        admissibility_records=(record(),),
        now=NOW,
    )

    assert assessment.state is EvidenceIntakeState.VALID
    assert assessment.package_ref.digest == digest("e")
    assert assessment.evaluated_claim_refs == ("admissibility-1",)
    assert assessment.claims_substantiated is True


def test_package_digest_mismatch_is_explicit():
    assessment = assess_evidence_intake(
        request(),
        package=package(package_digest=digest("f")),
        admissibility_records=(record(),),
        now=NOW,
    )

    assert assessment.state is EvidenceIntakeState.MISMATCHED
    assert "package_digest" in assessment.blocking_reasons[0]


def test_stale_package_blocks():
    assessment = assess_evidence_intake(
        request(max_package_age_seconds=60),
        package=package(created_at=NOW - timedelta(minutes=10)),
        admissibility_records=(record(),),
        now=NOW,
    )

    assert assessment.state is EvidenceIntakeState.STALE
    assert assessment.requires_human_review is True


def test_invalidated_package_blocks():
    assessment = assess_evidence_intake(
        request(),
        package=package(invalidated=True),
        admissibility_records=(record(),),
        now=NOW,
    )

    assert assessment.state is EvidenceIntakeState.INVALIDATED


def test_intended_use_mismatch_blocks():
    assessment = assess_evidence_intake(
        request(),
        package=package(permissible_uses=("background_only",)),
        admissibility_records=(record(),),
        now=NOW,
    )

    assert assessment.state is EvidenceIntakeState.USE_PROHIBITED


def test_unsupported_material_claim_blocks():
    assessment = assess_evidence_intake(
        request(),
        package=package(),
        admissibility_records=(
            record(disposition=ClaimDisposition.UNSUPPORTED),
        ),
        now=NOW,
    )

    assert assessment.state is EvidenceIntakeState.UNVERIFIED
    assert assessment.blocking_claim_refs == ("admissibility-1",)
    assert assessment.claims_substantiated is False


def test_partial_low_materiality_claim_is_constrained():
    assessment = assess_evidence_intake(
        request(),
        package=package(),
        admissibility_records=(
            record(
                disposition=ClaimDisposition.PARTIALLY_SUPPORTED,
                materiality=ClaimMateriality.LOW,
            ),
        ),
        now=NOW,
    )

    assert assessment.state is EvidenceIntakeState.CONSTRAINED
    assert assessment.constrained_claim_refs == ("admissibility-1",)
    assert assessment.blocks_consequential_action is True


def test_package_contradiction_is_not_hidden_by_supported_claim():
    assessment = assess_evidence_intake(
        request(),
        package=package(contradictions=("source-a conflicts with source-b",)),
        admissibility_records=(record(),),
        now=NOW,
    )

    assert assessment.state is EvidenceIntakeState.CONFLICTED


def test_failed_deterministic_workflow_criterion_blocks():
    evidence_request = request(
        workflow_required=True,
        expected_workflow_fingerprint=digest("4"),
        expected_node_fingerprint=digest("5"),
        expected_workflow_state_fingerprint=digest("6"),
    )
    assessment = assess_evidence_intake(
        evidence_request,
        package=package(),
        admissibility_records=(record(),),
        workflow_verification=workflow(
            accepted=False,
            criteria=(criterion(status="FAILED"),),
        ),
        now=NOW,
    )

    assert assessment.state is EvidenceIntakeState.UNVERIFIED
    assert any("Deterministic criterion" in reason for reason in assessment.blocking_reasons)


def test_exact_accepted_workflow_bundle_is_valid():
    evidence_request = request(
        workflow_required=True,
        expected_workflow_fingerprint=digest("4"),
        expected_node_fingerprint=digest("5"),
        expected_workflow_state_fingerprint=digest("6"),
    )
    assessment = assess_evidence_intake(
        evidence_request,
        package=package(),
        admissibility_records=(record(),),
        workflow_verification=workflow(),
        now=NOW,
    )

    assert assessment.state is EvidenceIntakeState.VALID
    assert assessment.workflow_bundle_fingerprint == digest("3")


def _configure_empty_plan(orchestrator):
    orchestrator.ensemble.instruments = {}
    orchestrator.dirigent.conduct = lambda _terrain: SimpleNamespace(
        internal=[],
        external=[],
        bench=[],
        thresholds={},
        context_health=1.0,
        context_warning=None,
        context_warning_detail=None,
    )


def test_orchestrator_blocks_missing_required_evidence_and_audits_state(tmp_path):
    orchestrator = VAIGOrchestrator(
        log_path=str(tmp_path / "audit.jsonl"),
        with_cakm=False,
    )
    _configure_empty_plan(orchestrator)

    result = orchestrator.evaluate(
        prompt="Approve payment",
        response="Approved",
        evidence_request=request(),
        evidence_now=NOW,
    )

    assert result.evidence_intake.state is EvidenceIntakeState.MISSING
    assert result.should_halt is True
    assert result.level is DistrustLevel.HALT

    entry = orchestrator.ensemble.worm.read_all()[0]
    assert entry["evidence_intake"]["state"] == "MISSING"
    assert entry["evidence_intake"]["execution_authority"] is False
    assert entry["evidence_intake"]["requires_reht_clearance"] is True


def test_orchestrator_accepts_exact_valid_evidence_binding(tmp_path):
    orchestrator = VAIGOrchestrator(
        log_path=str(tmp_path / "audit.jsonl"),
        with_cakm=False,
    )
    _configure_empty_plan(orchestrator)

    result = orchestrator.evaluate(
        prompt="Approve payment",
        response="Approved",
        evidence_request=request(),
        evidence_package=package(),
        claim_admissibility=(record(),),
        evidence_now=NOW,
    )

    assert result.evidence_intake.state is EvidenceIntakeState.VALID
    assert result.evidence_blocked is False
    assert result.should_halt is False
    assert result.level is DistrustLevel.TRUSTED


def test_orchestrator_rejects_unbound_evidence_inputs(tmp_path):
    orchestrator = VAIGOrchestrator(
        log_path=str(tmp_path / "audit.jsonl"),
        with_cakm=False,
    )
    _configure_empty_plan(orchestrator)

    result = orchestrator.evaluate(
        prompt="Approve payment",
        response="Approved",
        evidence_package=package(),
        claim_admissibility=(record(),),
        evidence_now=NOW,
    )

    assert result.evidence_intake.state is EvidenceIntakeState.MISMATCHED
    assert result.should_halt is True
