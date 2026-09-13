from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..memory_provider import canonical_digest
from .models import EvidenceReference, PublicationEventKind


INTEROPERABILITY_VERSION = "0.1.0"
DRAFT_DATA_SPACE_FEATURE_FLAG = "public_procurement_data_space_draft"


class ProcurementDataSpace(str, Enum):
    NATIONAL = "national_public_procurement_data_space"
    UNION = "union_public_procurement_data_space"


class InteroperabilityProfileState(str, Enum):
    DRAFT = "draft"
    ENABLED = "enabled"
    DISABLED = "disabled"


class CredentialVerificationState(str, Enum):
    VERIFIED = "verified"
    UNVERIFIED = "unverified"
    REVOKED = "revoked"
    EXPIRED = "expired"


class ProcurementInteroperabilityProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    target_data_space: ProcurementDataSpace
    schema_ref: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    state: InteroperabilityProfileState
    final_specification: bool = False
    required_feature_flag: str | None = None
    allowed_event_kinds: tuple[PublicationEventKind, ...]
    grants_authority: bool = False

    @model_validator(mode="after")
    def enforce_draft_boundary(self) -> "ProcurementInteroperabilityProfile":
        if self.grants_authority:
            raise ValueError("interoperability profile cannot grant authority")
        if not self.allowed_event_kinds:
            raise ValueError("allowed_event_kinds cannot be empty")
        if not self.final_specification and not self.required_feature_flag:
            raise ValueError("draft profile requires an explicit feature flag")
        return self


class ProcurementExportRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    record_id: str = Field(min_length=1)
    event_kind: PublicationEventKind
    object_ref: str = Field(min_length=1)
    object_type: str = Field(min_length=1)
    object_version: str = Field(min_length=1)
    source_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_receipt_refs: tuple[str, ...]
    normalized_payload: Mapping[str, Any]
    record_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    grants_authority: bool = False

    @model_validator(mode="after")
    def verify_record(self) -> "ProcurementExportRecord":
        if self.grants_authority:
            raise ValueError("export record cannot grant authority")
        if not self.source_receipt_refs:
            raise ValueError("export record requires source receipts")
        if self.record_digest != procurement_export_record_digest(self):
            raise ValueError("record_digest mismatch")
        return self


class ProcurementExportEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    interoperability_version: str = INTEROPERABILITY_VERSION
    export_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    procedure_ref: str = Field(min_length=1)
    profile_id: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    target_data_space: ProcurementDataSpace
    schema_ref: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    records: tuple[ProcurementExportRecord, ...]
    generated_at: datetime
    payload_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    grants_authority: bool = False
    published: bool = False

    @model_validator(mode="after")
    def verify_envelope(self) -> "ProcurementExportEnvelope":
        if self.grants_authority:
            raise ValueError("export envelope cannot grant authority")
        if self.published:
            raise ValueError("adapter cannot claim publication")
        if not self.records:
            raise ValueError("export envelope requires records")
        if tuple(sorted(record.record_id for record in self.records)) != tuple(
            record.record_id for record in self.records
        ):
            raise ValueError("export records must be deterministically ordered")
        if self.payload_digest != procurement_export_envelope_digest(self):
            raise ValueError("payload_digest mismatch")
        return self


class DigitalBusinessCredential(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    credential_id: str = Field(min_length=1)
    credential_type: str = Field(min_length=1)
    issuer_ref: str = Field(min_length=1)
    subject_ref: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    claims_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    issued_at: datetime
    expires_at: datetime | None = None
    verification_state: CredentialVerificationState
    verifier_ref: str | None = None
    revocation_ref: str | None = None
    grants_authority: bool = False

    @model_validator(mode="after")
    def validate_credential(self) -> "DigitalBusinessCredential":
        if self.grants_authority:
            raise ValueError("credential cannot grant procurement authority")
        if self.expires_at is not None and self.expires_at <= self.issued_at:
            raise ValueError("credential expiry must follow issuance")
        if self.verification_state is CredentialVerificationState.VERIFIED and not self.verifier_ref:
            raise ValueError("verified credential requires verifier_ref")
        return self


class EligibilityEvidenceObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    observation_id: str = Field(min_length=1)
    operator_ref: str = Field(min_length=1)
    criterion_code: str = Field(min_length=1)
    credential_id: str = Field(min_length=1)
    credential_type: str = Field(min_length=1)
    claims_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    verification_state: CredentialVerificationState
    observed_at: datetime
    evidence_ref: EvidenceReference | None = None
    observation_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    grants_authority: bool = False
    determines_eligibility: bool = False

    @model_validator(mode="after")
    def observation_is_evidence_only(self) -> "EligibilityEvidenceObservation":
        if self.grants_authority:
            raise ValueError("eligibility observation cannot grant authority")
        if self.determines_eligibility:
            raise ValueError("credential adapter cannot determine eligibility")
        if self.verification_state is CredentialVerificationState.VERIFIED and self.evidence_ref is None:
            raise ValueError("verified observation requires evidence_ref")
        if self.verification_state is not CredentialVerificationState.VERIFIED and self.evidence_ref is not None:
            raise ValueError("unverified observation cannot emit admissible evidence")
        if self.observation_digest != eligibility_observation_digest(self):
            raise ValueError("observation_digest mismatch")
        return self


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def default_interoperability_profiles() -> Mapping[str, ProcurementInteroperabilityProfile]:
    event_kinds = tuple(PublicationEventKind)
    profiles = (
        ProcurementInteroperabilityProfile(
            profile_id="nppds-draft",
            profile_version="2026.07-draft",
            target_data_space=ProcurementDataSpace.NATIONAL,
            schema_ref="urn:valo:procurement:nppds:draft",
            schema_version="2026.07-draft",
            state=InteroperabilityProfileState.DRAFT,
            final_specification=False,
            required_feature_flag=DRAFT_DATA_SPACE_FEATURE_FLAG,
            allowed_event_kinds=event_kinds,
        ),
        ProcurementInteroperabilityProfile(
            profile_id="union-ppds-draft",
            profile_version="2026.07-draft",
            target_data_space=ProcurementDataSpace.UNION,
            schema_ref="urn:valo:procurement:union-ppds:draft",
            schema_version="2026.07-draft",
            state=InteroperabilityProfileState.DRAFT,
            final_specification=False,
            required_feature_flag=DRAFT_DATA_SPACE_FEATURE_FLAG,
            allowed_event_kinds=event_kinds,
        ),
    )
    return {profile.profile_id: profile for profile in profiles}


def procurement_export_record_digest(record: ProcurementExportRecord) -> str:
    return canonical_digest(record.model_dump(mode="json", exclude={"record_digest"}))


def procurement_export_envelope_digest(envelope: ProcurementExportEnvelope) -> str:
    return canonical_digest(
        envelope.model_dump(mode="json", exclude={"payload_digest", "generated_at"})
    )


def eligibility_observation_digest(observation: EligibilityEvidenceObservation) -> str:
    return canonical_digest(
        observation.model_dump(mode="json", exclude={"observation_digest"})
    )


def build_procurement_export_record(
    *,
    record_id: str,
    event_kind: PublicationEventKind,
    object_ref: str,
    object_type: str,
    object_version: str,
    source_digest: str,
    source_receipt_refs: tuple[str, ...],
    normalized_payload: Mapping[str, Any],
) -> ProcurementExportRecord:
    payload = {
        "record_id": record_id,
        "event_kind": event_kind,
        "object_ref": object_ref,
        "object_type": object_type,
        "object_version": object_version,
        "source_digest": source_digest,
        "source_receipt_refs": tuple(sorted(set(source_receipt_refs))),
        "normalized_payload": dict(normalized_payload),
        "grants_authority": False,
    }
    provisional = ProcurementExportRecord.model_construct(
        **payload,
        record_digest="sha256:" + "0" * 64,
    )
    return ProcurementExportRecord(
        **payload,
        record_digest=procurement_export_record_digest(provisional),
    )


def build_procurement_export_envelope(
    *,
    export_id: str,
    tenant_id: str,
    procedure_ref: str,
    profile: ProcurementInteroperabilityProfile,
    records: tuple[ProcurementExportRecord, ...],
    feature_flags: Mapping[str, bool],
    generated_at: datetime,
) -> ProcurementExportEnvelope:
    if profile.state is InteroperabilityProfileState.DISABLED:
        raise ValueError("interoperability profile is disabled")
    if not profile.final_specification:
        flag = profile.required_feature_flag
        if flag is None or not feature_flags.get(flag, False):
            raise ValueError("draft interoperability profile requires enabled feature flag")
    if any(record.event_kind not in profile.allowed_event_kinds for record in records):
        raise ValueError("export contains event kind not allowed by profile")

    ordered = tuple(sorted(records, key=lambda item: item.record_id))
    payload = {
        "interoperability_version": INTEROPERABILITY_VERSION,
        "export_id": export_id,
        "tenant_id": tenant_id,
        "procedure_ref": procedure_ref,
        "profile_id": profile.profile_id,
        "profile_version": profile.profile_version,
        "target_data_space": profile.target_data_space,
        "schema_ref": profile.schema_ref,
        "schema_version": profile.schema_version,
        "records": ordered,
        "generated_at": _as_utc(generated_at),
        "grants_authority": False,
        "published": False,
    }
    provisional = ProcurementExportEnvelope.model_construct(
        **payload,
        payload_digest="sha256:" + "0" * 64,
    )
    return ProcurementExportEnvelope(
        **payload,
        payload_digest=procurement_export_envelope_digest(provisional),
    )


def observe_digital_business_credential(
    *,
    observation_id: str,
    operator_ref: str,
    criterion_code: str,
    credential: DigitalBusinessCredential,
    observed_at: datetime,
) -> EligibilityEvidenceObservation:
    now = _as_utc(observed_at)
    state = credential.verification_state
    if credential.subject_ref != operator_ref:
        state = CredentialVerificationState.UNVERIFIED
    elif credential.expires_at is not None and _as_utc(credential.expires_at) <= now:
        state = CredentialVerificationState.EXPIRED

    evidence_ref = None
    if state is CredentialVerificationState.VERIFIED:
        evidence_ref = EvidenceReference(
            evidence_id=f"credential-evidence:{credential.credential_id}",
            evidence_type="digital_business_credential",
            source_ref=credential.source_ref,
            content_digest=credential.claims_digest,
            issued_at=_as_utc(credential.issued_at),
            expires_at=_as_utc(credential.expires_at) if credential.expires_at else None,
        )

    payload = {
        "observation_id": observation_id,
        "operator_ref": operator_ref,
        "criterion_code": criterion_code,
        "credential_id": credential.credential_id,
        "credential_type": credential.credential_type,
        "claims_digest": credential.claims_digest,
        "verification_state": state,
        "observed_at": now,
        "evidence_ref": evidence_ref,
        "grants_authority": False,
        "determines_eligibility": False,
    }
    provisional = EligibilityEvidenceObservation.model_construct(
        **payload,
        observation_digest="sha256:" + "0" * 64,
    )
    return EligibilityEvidenceObservation(
        **payload,
        observation_digest=eligibility_observation_digest(provisional),
    )
