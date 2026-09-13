from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .memory_provider import MemoryRecord, MemoryStatus, canonical_digest


class HumanApprovalAttestation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    attestation_id: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    approver_id: str = Field(min_length=1)
    source_evidence_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_namespace: str = Field(min_length=1)
    approved_at: datetime
    expires_at: datetime

    @model_validator(mode="after")
    def validate_window(self) -> "HumanApprovalAttestation":
        if self.expires_at <= self.approved_at:
            raise ValueError("approval must expire after it is issued")
        return self


class SolPromotionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    request_id: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    source_memory_id: str = Field(min_length=1)
    source_snapshot_id: str = Field(min_length=1)
    source_evidence_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    target_namespace: str = Field(min_length=1)
    proposed_content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    requested_at: datetime

    @field_validator("target_namespace")
    @classmethod
    def safe_namespace(cls, value: str) -> str:
        if value.startswith("/") or ".." in value:
            raise ValueError("target_namespace must be a safe relative namespace")
        return value


class SolPromotionReceipt(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    receipt_id: str = Field(min_length=1)
    request_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    approval_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_memory_id: str = Field(min_length=1)
    source_snapshot_id: str = Field(min_length=1)
    target_namespace: str = Field(min_length=1)
    canonical_memory_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    promoted_at: datetime
    grants_authority: bool = False
    is_governance_clearance: bool = False
    is_execution_receipt: bool = False

    @model_validator(mode="after")
    def enforce_separation(self) -> "SolPromotionReceipt":
        if self.grants_authority or self.is_governance_clearance or self.is_execution_receipt:
            raise ValueError("SOL promotion receipt cannot grant authority or replace clearance/receipts")
        return self


def validate_promotion_candidate(record: MemoryRecord, *, stale: bool) -> None:
    if stale:
        raise ValueError("stale memory cannot be promoted")
    if record.status is not MemoryStatus.VALIDATED:
        raise ValueError("only validated memory can be promoted")


def execute_promotion(
    *,
    request: SolPromotionRequest,
    approval: HumanApprovalAttestation,
    record: MemoryRecord,
    content: Any,
    stale: bool,
    receipt_id: str,
    now: datetime | None = None,
) -> SolPromotionReceipt:
    current_time = now or datetime.now(timezone.utc)
    validate_promotion_candidate(record, stale=stale)

    if approval.principal_id != request.principal_id:
        raise ValueError("approval principal does not match request")
    if approval.source_evidence_digest != request.source_evidence_digest:
        raise ValueError("approval evidence scope does not match request")
    if approval.target_namespace != request.target_namespace:
        raise ValueError("approval namespace does not match request")
    if current_time > approval.expires_at:
        raise ValueError("approval has expired")
    if record.memory_id != request.source_memory_id:
        raise ValueError("source memory does not match request")
    if record.snapshot_id != request.source_snapshot_id:
        raise ValueError("source snapshot does not match request")

    actual_content_digest = canonical_digest(content)
    if actual_content_digest != record.content_digest:
        raise ValueError("source memory content digest mismatch")
    if actual_content_digest != request.proposed_content_digest:
        raise ValueError("proposed content digest mismatch")

    return SolPromotionReceipt(
        receipt_id=receipt_id,
        request_digest=canonical_digest(request.model_dump(mode="json")),
        approval_digest=canonical_digest(approval.model_dump(mode="json")),
        source_memory_id=record.memory_id,
        source_snapshot_id=record.snapshot_id,
        target_namespace=request.target_namespace,
        canonical_memory_digest=actual_content_digest,
        promoted_at=current_time,
    )


def verify_promotion_replay(
    *, request: SolPromotionRequest, approval: HumanApprovalAttestation, receipt: SolPromotionReceipt
) -> bool:
    return (
        receipt.request_digest == canonical_digest(request.model_dump(mode="json"))
        and receipt.approval_digest == canonical_digest(approval.model_dump(mode="json"))
        and receipt.target_namespace == request.target_namespace
        and receipt.source_memory_id == request.source_memory_id
        and receipt.source_snapshot_id == request.source_snapshot_id
        and receipt.canonical_memory_digest == request.proposed_content_digest
        and not receipt.grants_authority
        and not receipt.is_governance_clearance
        and not receipt.is_execution_receipt
    )
