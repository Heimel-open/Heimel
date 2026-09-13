"""Deterministic shadow evaluator for VALO Governed Newsroom.

The evaluator builds a claim-scoped EvidencePackage and a use-specific shadow
recommendation. It does not issue GovernanceClearance or execute publication.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable, List, Mapping, Optional, Sequence, Set

from src.valo_platform.canonical import canonical_digest
from src.valo_platform.models.core_receipt import ExecutionDecision
from src.valo_platform.report_integrity.models import ReportIntegrityResult
from src.valo_platform.verification_factory.models import (
    ClaimDisposition,
    ClaimRecord,
    EvidenceAdmissibilityRecord,
    EvidencePackage,
    RealityEvidence,
    SourceProfile,
    VerificationCase,
    VerificationFinding,
    VerificationFindingStatus,
    VerificationWorkOrder,
    VersionedRef,
)
from src.valo_platform.verification_factory.report_integrity_adapter import (
    adapt_report_integrity_findings,
)
from src.valo_platform.verification_factory.rules import (
    PreconditionDisposition,
    assess_claim_preconditions,
)
from src.valo_platform.verification_factory.source_integrity import (
    IntegrityPreconditionDisposition,
    SourceIntegrityAssessment,
    assess_source_integrity,
    build_public_integrity_card,
)

from .models import (
    NewsroomGovernanceInputs,
    NewsroomRiskTier,
    NewsroomShadowEvaluation,
)


def _ref(artifact_id: str, value: object, *, version: str = "v1") -> VersionedRef:
    safe_id = artifact_id.replace(" ", "-")
    return VersionedRef(
        artifact_id=safe_id,
        version=version,
        reference=f"valo://verification/{safe_id}/{version}",
        digest=canonical_digest(value),
    )


def _validate_bindings(
    *,
    case: VerificationCase,
    source_profiles: Sequence[SourceProfile],
    source_integrity: Mapping[str, SourceIntegrityAssessment],
    claim: ClaimRecord,
    evidence: Sequence[RealityEvidence],
    work_order: VerificationWorkOrder,
) -> None:
    if claim.case_id != case.case_id:
        raise ValueError("Claim is bound to another verification case")
    if work_order.case_id != case.case_id or work_order.claim_id != claim.claim_id:
        raise ValueError("Verification work order does not match case and claim")
    profile_ids = {profile.source_id for profile in source_profiles}
    if not profile_ids:
        raise ValueError("At least one source profile is required")
    if set(source_integrity) != profile_ids:
        raise ValueError(
            "Every source profile requires exactly one SourceIntegrityAssessment"
        )
    for record in evidence:
        if record.case_id != case.case_id or record.claim_id != claim.claim_id:
            raise ValueError("Evidence is bound to another case or claim")
        if record.source_id not in profile_ids:
            raise ValueError(
                f"Evidence source {record.source_id!r} lacks a source profile"
            )


def _permissible_uses(
    claim: ClaimRecord,
    assessments: Iterable[SourceIntegrityAssessment],
) -> List[str]:
    candidates: List[Set[str]] = [set(claim.intended_uses)]
    for assessment in assessments:
        if assessment.permissible_uses:
            candidates.append(set(assessment.permissible_uses))
    if not candidates:
        return []
    permitted = candidates[0]
    for candidate in candidates[1:]:
        permitted = permitted.intersection(candidate)
    return sorted(permitted)


def _prohibited_uses(
    claim: ClaimRecord,
    assessments: Iterable[SourceIntegrityAssessment],
) -> List[str]:
    prohibited = set(claim.prohibited_uses)
    for assessment in assessments:
        prohibited.update(assessment.prohibited_uses)
    return sorted(prohibited)


def _derive_disposition(
    *,
    source_dispositions: Iterable[IntegrityPreconditionDisposition],
    claim_disposition: PreconditionDisposition,
    findings: Sequence[VerificationFinding],
) -> ClaimDisposition:
    source_dispositions = set(source_dispositions)
    finding_statuses = {finding.status for finding in findings}

    if IntegrityPreconditionDisposition.INSUFFICIENT in source_dispositions:
        return ClaimDisposition.UNSUPPORTED
    if claim_disposition is PreconditionDisposition.CONFLICTED:
        return ClaimDisposition.CONFLICTED
    if VerificationFindingStatus.FAIL in finding_statuses:
        return ClaimDisposition.UNSUPPORTED
    if (
        IntegrityPreconditionDisposition.UNKNOWN in source_dispositions
        or claim_disposition is PreconditionDisposition.UNKNOWN
    ):
        return ClaimDisposition.UNKNOWN
    if (
        IntegrityPreconditionDisposition.REVIEW in source_dispositions
        or claim_disposition is PreconditionDisposition.INSUFFICIENT
        or VerificationFindingStatus.REVIEW in finding_statuses
        or VerificationFindingStatus.UNKNOWN in finding_statuses
        or VerificationFindingStatus.TIMEOUT in finding_statuses
    ):
        return ClaimDisposition.PARTIALLY_SUPPORTED
    return ClaimDisposition.SUPPORTED


def _shadow_recommendation(
    *,
    disposition: ClaimDisposition,
    governance_inputs: NewsroomGovernanceInputs,
) -> ExecutionDecision:
    if disposition is ClaimDisposition.UNSUPPORTED:
        return ExecutionDecision.DENY
    if disposition in {
        ClaimDisposition.CONFLICTED,
        ClaimDisposition.UNKNOWN,
        ClaimDisposition.UNTRACEABLE,
        ClaimDisposition.STALE,
    }:
        return ExecutionDecision.DEFER
    if disposition is ClaimDisposition.PARTIALLY_SUPPORTED:
        return (
            ExecutionDecision.MODIFY
            if governance_inputs.human_review_completed
            else ExecutionDecision.STEP_UP
        )
    if (
        governance_inputs.risk_tier
        in {
            NewsroomRiskTier.MATERIAL,
            NewsroomRiskTier.HIGH,
            NewsroomRiskTier.CRITICAL,
        }
        and not governance_inputs.human_review_completed
    ):
        return ExecutionDecision.STEP_UP
    return ExecutionDecision.ALLOW


def evaluate_newsroom_shadow(
    *,
    case: VerificationCase,
    source_profiles: Sequence[SourceProfile],
    source_integrity: Mapping[str, SourceIntegrityAssessment],
    claim: ClaimRecord,
    evidence: Sequence[RealityEvidence],
    work_order: VerificationWorkOrder,
    governance_inputs: NewsroomGovernanceInputs,
    report_integrity_results: Sequence[ReportIntegrityResult] = (),
    now: Optional[datetime] = None,
) -> NewsroomShadowEvaluation:
    """Build a replayable, non-authoritative newsroom evidence package."""

    now = now or datetime.now(timezone.utc)
    _validate_bindings(
        case=case,
        source_profiles=source_profiles,
        source_integrity=source_integrity,
        claim=claim,
        evidence=evidence,
        work_order=work_order,
    )
    material_usage = governance_inputs.risk_tier is not NewsroomRiskTier.LOW

    source_results = {
        profile.source_id: assess_source_integrity(
            profile,
            source_integrity[profile.source_id],
            material_usage=material_usage,
        )
        for profile in source_profiles
    }
    claim_result = assess_claim_preconditions(
        claim,
        list(evidence),
        list(source_profiles),
        work_order,
        now=now,
    )

    findings: List[VerificationFinding] = []
    for report_result in report_integrity_results:
        bundle = adapt_report_integrity_findings(
            report_result,
            case_id=case.case_id,
            claim_id=claim.claim_id,
            work_order_id=work_order.work_order_id,
            evidence_refs=[record.evidence_id for record in evidence],
            decided_at=now,
        )
        findings.extend(bundle.findings)

    disposition = _derive_disposition(
        source_dispositions=[
            result.disposition for result in source_results.values()
        ],
        claim_disposition=claim_result.disposition,
        findings=findings,
    )

    source_profile_refs = [
        _ref(f"source-profile:{profile.source_id}", profile)
        for profile in source_profiles
    ]
    finding_refs = [
        _ref(f"finding:{finding.finding_id}", finding)
        for finding in findings
    ]
    claim_ref = _ref(f"claim:{claim.claim_id}", claim)
    work_order_ref = _ref(f"work-order:{work_order.work_order_id}", work_order)
    policy_ref = work_order.policy_ref

    permissible = _permissible_uses(claim, source_integrity.values())
    prohibited = _prohibited_uses(claim, source_integrity.values())

    unresolved_questions: List[str] = []
    contradictions: List[str] = []
    limitations: List[str] = []

    for source_id, result in source_results.items():
        unresolved_questions.extend(
            f"{source_id}:{failure.code}" for failure in result.failures
        )
    unresolved_questions.extend(
        f"claim:{failure.code}" for failure in claim_result.failures
    )
    for assessment in source_integrity.values():
        unresolved_questions.extend(assessment.unresolved_questions)
    for finding in findings:
        contradictions.extend(finding.contradiction_refs)
        limitations.extend(finding.limitations)

    admissibility_payload = {
        "case_id": case.case_id,
        "claim_id": claim.claim_id,
        "disposition": disposition.value,
        "source_profile_refs": [ref.digest for ref in source_profile_refs],
        "evidence_refs": [record.content_digest for record in evidence],
        "finding_refs": [ref.digest for ref in finding_refs],
        "independent_root_count": claim_result.independent_root_count,
        "permissible_uses": permissible,
        "prohibited_uses": prohibited,
        "unresolved_conflicts": sorted(set(contradictions)),
        "limitations": sorted(set(limitations)),
        "policy_ref": policy_ref.digest,
        "decided_at": now,
    }
    admissibility = EvidenceAdmissibilityRecord(
        admissibility_id=(
            f"newsroom-admissibility:{claim.claim_id}:"
            f"{canonical_digest(admissibility_payload)[-16:]}"
        ),
        case_id=case.case_id,
        claim_id=claim.claim_id,
        disposition=disposition,
        source_profile_refs=[ref.reference for ref in source_profile_refs],
        evidence_refs=[record.evidence_id for record in evidence],
        finding_refs=[finding.finding_id for finding in findings],
        independent_root_count=claim_result.independent_root_count,
        permissible_uses=permissible,
        prohibited_uses=prohibited,
        unresolved_conflicts=sorted(set(contradictions)),
        limitations=sorted(set(limitations)),
        policy_ref=policy_ref,
        decided_at=now,
    )
    admissibility_ref = _ref(
        f"admissibility:{admissibility.admissibility_id}",
        admissibility,
    )

    package_payload = {
        "case_id": case.case_id,
        "package_version": "v1",
        "claim_refs": [claim_ref],
        "source_profile_refs": source_profile_refs,
        "evidence_refs": [record.observation_ref for record in evidence],
        "work_order_refs": [work_order_ref],
        "finding_refs": finding_refs,
        "admissibility_refs": [admissibility_ref],
        "governance_inputs": governance_inputs,
        "unresolved_questions": sorted(set(unresolved_questions)),
        "contradictions": sorted(set(contradictions)),
        "permissible_uses": permissible,
        "prohibited_uses": prohibited,
        "created_at": now,
    }
    package_digest = canonical_digest(package_payload)
    evidence_package = EvidencePackage(
        package_id=f"newsroom-package:{case.case_id}:{claim.claim_id}",
        case_id=case.case_id,
        package_version="v1",
        package_digest=package_digest,
        claim_refs=[claim_ref],
        source_profile_refs=source_profile_refs,
        evidence_refs=[record.observation_ref for record in evidence],
        work_order_refs=[work_order_ref],
        finding_refs=finding_refs,
        admissibility_refs=[admissibility_ref],
        unresolved_questions=sorted(set(unresolved_questions)),
        contradictions=sorted(set(contradictions)),
        permissible_uses=permissible,
        prohibited_uses=prohibited,
        created_at=now,
    )

    recommendation = _shadow_recommendation(
        disposition=disposition,
        governance_inputs=governance_inputs,
    )
    recommendation_reasons = [
        f"CLAIM_{disposition.value}",
        *sorted(set(unresolved_questions)),
    ]
    required_conditions: List[str] = []
    if not governance_inputs.human_review_completed and recommendation in {
        ExecutionDecision.STEP_UP,
        ExecutionDecision.DEFER,
    }:
        required_conditions.append(
            f"Accountable editor review required: {governance_inputs.accountable_editor_id}"
        )
    if recommendation is ExecutionDecision.MODIFY:
        required_conditions.append(
            "Narrow wording and preserve source, funding, AI-origin and uncertainty disclosures"
        )
    if not permissible:
        required_conditions.append(
            "No permitted use remains after intersecting claim and source constraints"
        )

    metrics = {
        "source_count": float(len(source_profiles)),
        "evidence_count": float(len(evidence)),
        "independent_root_count": float(claim_result.independent_root_count),
        "finding_count": float(len(findings)),
        "finding_fail_count": float(
            sum(finding.status is VerificationFindingStatus.FAIL for finding in findings)
        ),
        "finding_review_count": float(
            sum(finding.status is VerificationFindingStatus.REVIEW for finding in findings)
        ),
        "unresolved_count": float(len(set(unresolved_questions))),
    }

    return NewsroomShadowEvaluation(
        case_id=case.case_id,
        claim_id=claim.claim_id,
        source_ids=sorted(profile.source_id for profile in source_profiles),
        governance_inputs=governance_inputs,
        source_preconditions=source_results,
        claim_preconditions=claim_result,
        report_findings=findings,
        admissibility=admissibility,
        evidence_package=evidence_package,
        public_integrity_cards=[
            build_public_integrity_card(
                profile,
                source_integrity[profile.source_id],
            )
            for profile in source_profiles
        ],
        shadow_reht_recommendation=recommendation,
        recommendation_reasons=recommendation_reasons,
        required_conditions=required_conditions,
        prohibited_uses=prohibited,
        metrics=metrics,
    )


__all__ = ["evaluate_newsroom_shadow"]
