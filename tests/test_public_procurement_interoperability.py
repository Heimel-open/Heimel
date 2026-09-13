from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from valo_platform.public_procurement.interoperability import (
    DRAFT_DATA_SPACE_FEATURE_FLAG,
    CredentialVerificationState,
    DigitalBusinessCredential,
    EligibilityEvidenceObservation,
    InteroperabilityProfileState,
    ProcurementDataSpace,
    ProcurementExportEnvelope,
    ProcurementExportRecord,
    build_procurement_export_envelope,
    build_procurement_export_record,
    default_interoperability_profiles,
    observe_digital_business_credential,
)
from valo_platform.public_procurement.models import PublicationEventKind


NOW = datetime(2026, 7, 29, 20, 0, tzinfo=timezone.utc)
DIGEST_A = "sha256:" + "a" * 64
DIGEST_B = "sha256:" + "b" * 64


def export_record(record_id: str = "record:001") -> ProcurementExportRecord:
    return build_procurement_export_record(
        record_id=record_id,
        event_kind=PublicationEventKind.AWARD,
        object_ref="award:2026-001",
        object_type="AwardDecision",
        object_version="0.1.0",
        source_digest=DIGEST_A,
        source_receipt_refs=("receipt:clearance:1", "receipt:execution:1"),
        normalized_payload={
            "award_id": "award:2026-001",
            "procedure_ref": "procedure:2026-001",
            "operator_ref": "operator:987654321",
        },
    )


def credential(
    *,
    subject_ref: str = "operator:987654321",
    verification_state: CredentialVerificationState = CredentialVerificationState.VERIFIED,
    expires_at: datetime | None = None,
) -> DigitalBusinessCredential:
    return DigitalBusinessCredential(
        credential_id="credential:operator:987654321:v4",
        credential_type="economic_operator_registration",
        issuer_ref="registry:brreg",
        subject_ref=subject_ref,
        source_ref="credential-store:credential:operator:987654321:v4",
        claims_digest=DIGEST_B,
        issued_at=NOW - timedelta(days=30),
        expires_at=expires_at or NOW + timedelta(days=30),
        verification_state=verification_state,
        verifier_ref=(
            "verifier:business-credential:1"
            if verification_state is CredentialVerificationState.VERIFIED
            else None
        ),
    )


def test_default_profiles_are_draft_feature_flagged_and_not_final() -> None:
    profiles = default_interoperability_profiles()

    assert set(profiles) == {"nppds-draft", "union-ppds-draft"}
    assert profiles["nppds-draft"].target_data_space is ProcurementDataSpace.NATIONAL
    assert profiles["union-ppds-draft"].target_data_space is ProcurementDataSpace.UNION
    assert all(profile.state is InteroperabilityProfileState.DRAFT for profile in profiles.values())
    assert all(profile.final_specification is False for profile in profiles.values())
    assert all(
        profile.required_feature_flag == DRAFT_DATA_SPACE_FEATURE_FLAG
        for profile in profiles.values()
    )


def test_draft_export_fails_closed_without_feature_flag() -> None:
    profile = default_interoperability_profiles()["nppds-draft"]

    with pytest.raises(ValueError, match="requires enabled feature flag"):
        build_procurement_export_envelope(
            export_id="export:1",
            tenant_id="tenant:buyer-1",
            procedure_ref="procedure:2026-001",
            profile=profile,
            records=(export_record(),),
            feature_flags={},
            generated_at=NOW,
        )


def test_export_is_deterministic_ordered_and_does_not_claim_publication() -> None:
    profile = default_interoperability_profiles()["nppds-draft"]
    later = build_procurement_export_record(
        record_id="record:002",
        event_kind=PublicationEventKind.CONTRACT,
        object_ref="contract:2026-001",
        object_type="PublicContract",
        object_version="0.1.0",
        source_digest=DIGEST_B,
        source_receipt_refs=("receipt:contract:1",),
        normalized_payload={"contract_id": "contract:2026-001"},
    )

    first = build_procurement_export_envelope(
        export_id="export:1",
        tenant_id="tenant:buyer-1",
        procedure_ref="procedure:2026-001",
        profile=profile,
        records=(later, export_record()),
        feature_flags={DRAFT_DATA_SPACE_FEATURE_FLAG: True},
        generated_at=NOW,
    )
    second = build_procurement_export_envelope(
        export_id="export:1",
        tenant_id="tenant:buyer-1",
        procedure_ref="procedure:2026-001",
        profile=profile,
        records=(export_record(), later),
        feature_flags={DRAFT_DATA_SPACE_FEATURE_FLAG: True},
        generated_at=NOW + timedelta(hours=1),
    )

    assert tuple(record.record_id for record in first.records) == ("record:001", "record:002")
    assert first.payload_digest == second.payload_digest
    assert first.published is False
    assert first.grants_authority is False


def test_export_record_requires_receipts_and_rejects_tampering() -> None:
    with pytest.raises(ValidationError, match="source receipts"):
        build_procurement_export_record(
            record_id="record:bad",
            event_kind=PublicationEventKind.AWARD,
            object_ref="award:bad",
            object_type="AwardDecision",
            object_version="0.1.0",
            source_digest=DIGEST_A,
            source_receipt_refs=(),
            normalized_payload={"award_id": "award:bad"},
        )

    payload = export_record().model_dump(mode="json")
    payload["object_ref"] = "award:tampered"
    with pytest.raises(ValidationError, match="record_digest"):
        ProcurementExportRecord(**payload)


def test_export_envelope_cannot_claim_publication_or_authority() -> None:
    profile = default_interoperability_profiles()["nppds-draft"]
    envelope = build_procurement_export_envelope(
        export_id="export:1",
        tenant_id="tenant:buyer-1",
        procedure_ref="procedure:2026-001",
        profile=profile,
        records=(export_record(),),
        feature_flags={DRAFT_DATA_SPACE_FEATURE_FLAG: True},
        generated_at=NOW,
    )
    payload = envelope.model_dump(mode="json")
    payload["published"] = True
    with pytest.raises(ValidationError, match="cannot claim publication"):
        ProcurementExportEnvelope(**payload)

    payload = envelope.model_dump(mode="json")
    payload["grants_authority"] = True
    with pytest.raises(ValidationError, match="cannot grant authority"):
        ProcurementExportEnvelope(**payload)


def test_verified_matching_credential_emits_evidence_not_eligibility() -> None:
    observation = observe_digital_business_credential(
        observation_id="observation:1",
        operator_ref="operator:987654321",
        criterion_code="registration",
        credential=credential(),
        observed_at=NOW,
    )

    assert observation.verification_state is CredentialVerificationState.VERIFIED
    assert observation.evidence_ref is not None
    assert observation.evidence_ref.evidence_type == "digital_business_credential"
    assert observation.determines_eligibility is False
    assert observation.grants_authority is False


def test_expired_or_wrong_subject_credential_emits_no_admissible_evidence() -> None:
    expired = observe_digital_business_credential(
        observation_id="observation:expired",
        operator_ref="operator:987654321",
        criterion_code="registration",
        credential=credential(expires_at=NOW - timedelta(seconds=1)),
        observed_at=NOW,
    )
    wrong_subject = observe_digital_business_credential(
        observation_id="observation:wrong-subject",
        operator_ref="operator:987654321",
        criterion_code="registration",
        credential=credential(subject_ref="operator:attacker"),
        observed_at=NOW,
    )

    assert expired.verification_state is CredentialVerificationState.EXPIRED
    assert expired.evidence_ref is None
    assert wrong_subject.verification_state is CredentialVerificationState.UNVERIFIED
    assert wrong_subject.evidence_ref is None


def test_observation_digest_rejects_tampering() -> None:
    observation = observe_digital_business_credential(
        observation_id="observation:1",
        operator_ref="operator:987654321",
        criterion_code="registration",
        credential=credential(),
        observed_at=NOW,
    )
    payload = observation.model_dump(mode="json")
    payload["criterion_code"] = "different"

    with pytest.raises(ValidationError, match="observation_digest"):
        EligibilityEvidenceObservation(**payload)
