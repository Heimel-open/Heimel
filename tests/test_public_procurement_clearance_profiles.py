from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

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
    ProcurementClearanceProfile,
    ProcurementProfileId,
    assess_procurement_action_case,
    default_clearance_profiles,
)


NOW = datetime(2026, 7, 29, 18, 0, tzinfo=timezone.utc)
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64
DIGEST_C = "sha256:" + "c" * 64


def evidence(evidence_id: str, evidence_type: str, *, stale: bool = False) -> EvidenceReference:
    return EvidenceReference(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        source_ref=f"source:{evidence_id}",
        content_digest=DIGEST_A,
        issued_at=NOW - timedelta(days=2),
        expires_at=NOW - timedelta(seconds=1) if stale else NOW + timedelta(days=30),
    )


def authority() -> AuthorityBinding:
    return AuthorityBinding(
        principal_id="principal:procurement-director",
        mandate_ref="mandate:procurement:2026",
        delegation_ref="delegation:procurement:5m",
        authority_version="3",
        valid_at=NOW,
        evidence_refs=("evidence:authority:3",),
    )


def action_case(
    *,
    commit_type: CommitActionType = CommitActionType.COMMIT_AWARD,
    evidence_types: tuple[str, ...] = (
        "tender_evaluation",
        "eligibility_attestation",
        "delegation_attestation",
    ),
    stale_type: str | None = None,
):
    return build_procurement_action_case(
        case_id="case:procurement:1",
        action_ref="procurement:procedure:2026-001",
        purpose="Perform the procurement action under the approved need",
        principal_id="principal:procurement-director",
        mandate_ref="mandate:procurement:2026",
        authority=authority(),
        procedure_ref="procedure:2026-001",
        contract_ref="contract:2026-001",
        operator_ref="operator:987654321",
        policy_version="procurement-policy:2026.7",
        criteria_versions=("criteria:2026-001:v3",),
        evidence_refs=tuple(
            evidence(
                f"evidence:{index}",
                evidence_type,
                stale=evidence_type == stale_type,
            )
            for index, evidence_type in enumerate(evidence_types, start=1)
        ),
        current_state_digest=DIGEST_B,
        risk_level=RiskLevel.HIGH,
        reversible=False,
        consequence="Create or modify an external procurement consequence",
        requested_commit=RequestedExternalCommit(
            action_type=commit_type,
            target_system="eprocurement:no:buyer-1",
            resource_ref="procedure:2026-001",
            payload_digest=DIGEST_C,
            idempotency_key=f"commit:{commit_type.value}:1",
            reversible=False,
            consequence="Commit the exact procurement action",
        ),
        created_at=NOW,
    )


def test_default_profiles_cover_all_required_procurement_actions() -> None:
    profiles = default_clearance_profiles()

    assert len(profiles) == 11
    assert set(profiles) == set(ProcurementProfileId)
    assert all(profile.reht_clearance_required for profile in profiles.values())
    assert all(profile.grants_authority is False for profile in profiles.values())


def test_complete_award_case_is_ready_for_reht_not_authorized() -> None:
    profile = default_clearance_profiles()[ProcurementProfileId.AWARD]

    assessment = assess_procurement_action_case(
        action_case=action_case(),
        profile=profile,
        observed_at=NOW,
    )

    assert assessment.disposition is AssessmentDisposition.READY_FOR_REHT
    assert assessment.reht_clearance_required is True
    assert assessment.grants_authority is False


def test_missing_mandatory_evidence_requires_gathering() -> None:
    profile = default_clearance_profiles()[ProcurementProfileId.AWARD]

    assessment = assess_procurement_action_case(
        action_case=action_case(evidence_types=("tender_evaluation",)),
        profile=profile,
        observed_at=NOW,
    )

    assert assessment.disposition is AssessmentDisposition.GATHER_EVIDENCE
    assert assessment.missing_evidence == ("authority_evidence", "eligibility")


def test_stale_bound_evidence_requires_step_up() -> None:
    profile = default_clearance_profiles()[ProcurementProfileId.AWARD]

    assessment = assess_procurement_action_case(
        action_case=action_case(stale_type="eligibility_attestation"),
        profile=profile,
        observed_at=NOW,
    )

    assert assessment.disposition is AssessmentDisposition.STEP_UP_RECOMMENDED
    assert assessment.stale_evidence == ("evidence:2",)


def test_bank_change_invalidates_payment_readiness() -> None:
    profile = default_clearance_profiles()[ProcurementProfileId.PAYMENT]
    payment_case = action_case(
        commit_type=CommitActionType.EXECUTE_PAYMENT,
        evidence_types=("invoice", "delivery_attestation", "bank_account_verification"),
    )

    assessment = assess_procurement_action_case(
        action_case=payment_case,
        profile=profile,
        observed_at=NOW,
        changed_fields=("bank_details",),
    )

    assert assessment.disposition is AssessmentDisposition.STEP_UP_RECOMMENDED
    assert assessment.triggered_changes == ("bank_changed",)


def test_wrong_commit_type_fails_closed() -> None:
    profile = default_clearance_profiles()[ProcurementProfileId.AWARD]

    assessment = assess_procurement_action_case(
        action_case=action_case(commit_type=CommitActionType.EXECUTE_PAYMENT),
        profile=profile,
        observed_at=NOW,
    )

    assert assessment.disposition is AssessmentDisposition.FAIL_CLOSED
    assert assessment.commit_type_valid is False


def test_profile_cannot_disable_reht_or_grant_authority() -> None:
    with pytest.raises(ValidationError, match="require REHT"):
        ProcurementClearanceProfile(
            profile_id=ProcurementProfileId.AWARD,
            required_context=("authority",),
            reht_clearance_required=False,
        )

    with pytest.raises(ValidationError, match="cannot grant authority"):
        ProcurementClearanceProfile(
            profile_id=ProcurementProfileId.AWARD,
            required_context=("authority",),
            grants_authority=True,
        )
