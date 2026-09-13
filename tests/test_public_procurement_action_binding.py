from datetime import datetime, timedelta, timezone

from valo_platform.public_procurement import (
    AuthorityBinding,
    CommitActionType,
    EvidenceReference,
    RequestedExternalCommit,
    RiskLevel,
    build_procurement_action_case,
)
from valo_platform.public_procurement.clearance_profiles import (
    AssessmentDisposition,
    ProcurementProfileId,
    assess_procurement_action_case,
    default_clearance_profiles,
)


NOW = datetime(2026, 7, 29, 19, 0, tzinfo=timezone.utc)
DIGEST = "sha256:" + "a" * 64


def evidence(evidence_id: str, evidence_type: str, *, stale: bool = False) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source_ref=f"source:{evidence_id}",
        content_digest=DIGEST,
        issued_at=NOW - timedelta(days=2),
        expires_at=NOW - timedelta(seconds=1) if stale else NOW + timedelta(days=30),
    )


def award_case(extra_evidence: tuple[EvidenceReference, ...] = ()):
    authority = AuthorityBinding(
        principal_id="principal:director",
        mandate_ref="mandate:procurement",
        authority_version="4",
        valid_at=NOW,
    )
    return build_procurement_action_case(
        case_id="case:award:binding",
        action_ref="award:procedure:1",
        purpose="Award contract",
        principal_id=authority.principal_id,
        mandate_ref=authority.mandate_ref,
        authority=authority,
        procedure_ref="procedure:1",
        contract_ref="contract:1",
        operator_ref="operator:1",
        policy_version="policy:4",
        criteria_versions=("criteria:4",),
        evidence_refs=(
            evidence("evaluation", "tender_evaluation"),
            evidence("eligibility", "eligibility_attestation"),
            evidence("authority", "delegation_attestation"),
        )
        + extra_evidence,
        current_state_digest=DIGEST,
        risk_level=RiskLevel.HIGH,
        reversible=False,
        consequence="Create public contract entitlement",
        requested_commit=RequestedExternalCommit(
            action_type=CommitActionType.COMMIT_AWARD,
            target_system="eprocurement",
            resource_ref="procedure:1",
            payload_digest=DIGEST,
            idempotency_key="award:1",
            reversible=False,
            consequence="Commit award",
        ),
        created_at=NOW,
    )


def test_every_commit_type_is_bound_to_a_clearance_profile() -> None:
    profiles = default_clearance_profiles()
    covered = {
        action_type
        for profile in profiles.values()
        for action_type in profile.allowed_commit_types
    }

    assert covered == set(CommitActionType)


def test_extended_actions_have_exact_profile_bindings() -> None:
    profiles = default_clearance_profiles()

    assert profiles[ProcurementProfileId.CRITERIA_WEIGHTING].allowed_commit_types == (
        CommitActionType.APPROVE_CRITERIA,
    )
    assert CommitActionType.REINSTATE_OPERATOR in profiles[
        ProcurementProfileId.EXCLUSION_REINSTATEMENT
    ].allowed_commit_types
    assert CommitActionType.RENEW_CONTRACT in profiles[
        ProcurementProfileId.TERMINATION_RENEWAL
    ].allowed_commit_types
    assert CommitActionType.EXTEND_CONTRACT in profiles[
        ProcurementProfileId.TERMINATION_RENEWAL
    ].allowed_commit_types
    assert profiles[ProcurementProfileId.EMERGENCY_PROCEDURE].allowed_commit_types == (
        CommitActionType.INVOKE_EMERGENCY_PROCEDURE,
    )


def test_irrelevant_stale_evidence_does_not_trigger_step_up() -> None:
    assessment = assess_procurement_action_case(
        action_case=award_case(
            extra_evidence=(evidence("old-weather", "weather_signal", stale=True),)
        ),
        profile=default_clearance_profiles()[ProcurementProfileId.AWARD],
        observed_at=NOW,
    )

    assert assessment.disposition is AssessmentDisposition.READY_FOR_REHT
    assert assessment.stale_evidence == ()
