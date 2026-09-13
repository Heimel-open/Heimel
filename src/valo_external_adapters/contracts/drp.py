from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class DrpActionDescriptor(BaseModel):
    operation: str
    resource: str
    constraints: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_descriptor(self) -> DrpActionDescriptor:
        if not self.operation or not self.resource:
            raise ValueError("DRP action operation and resource are required")
        return self


class DrpScope(BaseModel):
    version: str = "1.0"
    allowed_actions: tuple[DrpActionDescriptor, ...] = Field(alias="allowedActions")
    denied_actions: tuple[DrpActionDescriptor, ...] = Field(
        default=(), alias="deniedActions"
    )

    model_config = ConfigDict(
        extra="forbid", frozen=True, populate_by_name=True
    )


class DrpTimeWindow(BaseModel):
    not_before: datetime = Field(alias="notBefore")
    not_after: datetime = Field(alias="notAfter")

    model_config = ConfigDict(
        extra="forbid", frozen=True, populate_by_name=True
    )

    @model_validator(mode="after")
    def validate_window(self) -> DrpTimeWindow:
        if self.not_after <= self.not_before:
            raise ValueError("DRP time window must have positive duration")
        return self


class DrpReauthPolicy(BaseModel):
    seconds_before_expiry: int = Field(300, alias="secondsBeforeExpiry", ge=0)
    trust_score_below: float = Field(50, alias="trustScoreBelow", ge=0, le=100)
    on_authority_state_drift: Literal["block", "reauth"] = Field(
        "reauth", alias="onAuthorityStateDrift"
    )

    model_config = ConfigDict(
        extra="forbid", frozen=True, populate_by_name=True
    )


class DrpDelegationReceipt(BaseModel):
    receipt_id: str = Field(alias="receiptId", pattern=r"^rec_[0-9a-f]{64}$")
    schema_version: Literal["1.0"] = Field(alias="schemaVersion")
    time_window: DrpTimeWindow = Field(alias="timeWindow")
    public_key: dict[str, Any] = Field(alias="publicKey")
    scope: DrpScope
    boundaries: tuple[str, ...]
    operator_instructions_hash: str = Field(
        alias="operatorInstructionsHash", pattern=r"^sha256:[0-9a-f]{64}$"
    )
    canonical_payload: str = Field(alias="canonicalPayload")
    signature: str
    operator_instructions: str | None = Field(None, alias="operatorInstructions")
    model_commitment: str | None = Field(
        None, alias="modelCommitment", pattern=r"^sha256:[0-9a-f]{64}$"
    )
    metadata: dict[str, str] = Field(default_factory=dict)
    tool_schema_hash: str | None = Field(
        None, alias="toolSchemaHash", pattern=r"^sha256:[0-9a-f]{64}$"
    )
    discovery_metadata: dict[str, Any] | None = Field(None, alias="discoveryMetadata")
    log_entry_hash: str | None = Field(
        None, alias="logEntryHash", pattern=r"^sha256:[0-9a-f]{64}$"
    )
    trusted_sources: tuple[str, ...] | None = Field(None, alias="trustedSources")
    revocation_required: bool = Field(False, alias="revocationRequired")
    parent_receipt_id: str | None = Field(
        None, alias="parentReceiptId", pattern=r"^rec_[0-9a-f]{64}$"
    )
    orchestrator_signature: str | None = Field(None, alias="orchestratorSignature")
    provider_update_policy_id: str | None = Field(None, alias="providerUpdatePolicyId")
    tool_output_hash: str | None = Field(
        None, alias="toolOutputHash", pattern=r"^sha256:[0-9a-f]{64}$"
    )
    authority_state_commitment: str | None = Field(
        None, alias="authorityStateCommitment", pattern=r"^[0-9a-f]{64}$"
    )
    reauth_policy: DrpReauthPolicy | None = Field(None, alias="reauthPolicy")

    model_config = ConfigDict(
        extra="forbid", frozen=True, populate_by_name=True
    )

    @model_validator(mode="after")
    def validate_receipt(self) -> DrpDelegationReceipt:
        if not self.boundaries:
            raise ValueError("DRP boundaries must not be empty")
        if not self.canonical_payload or not self.signature or not self.public_key:
            raise ValueError("DRP cryptographic envelope is incomplete")
        if self.parent_receipt_id and not self.orchestrator_signature:
            raise ValueError("DRP sub-receipt requires orchestratorSignature")
        if not self.parent_receipt_id and self.orchestrator_signature:
            raise ValueError("orchestratorSignature requires parentReceiptId")
        return self


class DrpVerificationEvidence(BaseModel):
    receipt_id: str = Field(pattern=r"^rec_[0-9a-f]{64}$")
    signature_verified: bool
    canonical_payload_verified: bool
    log_anchor_verified: bool
    revocation_checked: bool
    revoked: bool = False
    orchestrator_binding_verified: bool | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)


class DrpInteropAssessment(BaseModel):
    schema_version: Literal["valo.drp_interop_assessment.v1"] = (
        "valo.drp_interop_assessment.v1"
    )
    receipt_id: str
    admissible_as_evidence: bool
    reasons: tuple[str, ...] = ()
    authority_state_match: bool | None = None
    requires_reht: Literal[True] = True
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    evidence_digest: str

    model_config = ConfigDict(extra="forbid", frozen=True)
