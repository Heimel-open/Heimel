"""Versioned evidence contracts for Veritas Edge V1.

Veritas records observable facts and cryptographic bindings. These contracts do
not contain policy evaluation or execution authority.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from valo_edge.contracts import ConsequenceDecision, SignatureV1, sha256_digest
from valo_edge.gateway import DriverExecutionStatus


VERITAS_CONTRACT_VERSION = "valo.edge.veritas.v1"
VERITAS_GENESIS_DIGEST = "sha256:" + ("0" * 64)


class VeritasRecordType(str, Enum):
    BOOT_CONTINUITY = "BOOT_CONTINUITY"
    AUTHORIZATION = "AUTHORIZATION"
    ENFORCEMENT = "ENFORCEMENT"
    EXECUTION_OBSERVATION = "EXECUTION_OBSERVATION"
    COMPENSATION = "COMPENSATION"
    RECONCILIATION = "RECONCILIATION"


class ConsequenceEvidenceState(str, Enum):
    """What the execution boundary can actually evidence, without overclaiming."""

    DRIVER_REPORTED_EXECUTED = "DRIVER_REPORTED_EXECUTED"
    DRIVER_REPORTED_PARTIAL = "DRIVER_REPORTED_PARTIAL"
    GATEWAY_REJECTED_NO_DRIVER_CALL = "GATEWAY_REJECTED_NO_DRIVER_CALL"
    DRIVER_REPORTED_FAILED = "DRIVER_REPORTED_FAILED"
    UNKNOWN_AFTER_TIMEOUT = "UNKNOWN_AFTER_TIMEOUT"


class CompensationStatus(str, Enum):
    PLANNED = "PLANNED"
    EXECUTED = "EXECUTED"
    FAILED = "FAILED"


class BootContinuityReceiptV1(BaseModel):
    contract_version: str = VERITAS_CONTRACT_VERSION
    receipt_id: str
    device_id: str
    boot_epoch: str
    previous_boot_epoch: Optional[str] = None
    previous_tail_digest: str
    recorded_at_iso: str

    def compute_digest(self) -> str:
        return sha256_digest(self)


class AuthorizationReceiptV1(BaseModel):
    contract_version: str = VERITAS_CONTRACT_VERSION
    receipt_id: str
    device_id: str
    boot_epoch: str
    proposal_digest: str
    clearance_digest: str
    authority_envelope_digest: str
    decision: ConsequenceDecision
    permit_id: Optional[str] = None
    permit_uses: int = Field(default=0, ge=0)
    recorded_at_iso: str

    def compute_digest(self) -> str:
        return sha256_digest(self)


class EnforcementReceiptV1(BaseModel):
    contract_version: str = VERITAS_CONTRACT_VERSION
    receipt_id: str
    device_id: str
    boot_epoch: str
    proposal_digest: str
    clearance_digest: str
    enforcement_digest: str
    device_command_digest: str
    permit_id: Optional[str] = None
    permit_use_index: Optional[int] = Field(default=None, ge=0)
    accepted: bool
    gateway_id: str
    recorded_at_iso: str

    def compute_digest(self) -> str:
        return sha256_digest(self)


class ExecutionObservationReceiptV1(BaseModel):
    contract_version: str = VERITAS_CONTRACT_VERSION
    receipt_id: str
    device_id: str
    boot_epoch: str
    enforcement_digest: str
    driver_outcome_digest: str
    driver_status: DriverExecutionStatus
    consequence_state: ConsequenceEvidenceState
    observed_output: Dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
    error_detail: Optional[str] = None
    physical_observation_digest: Optional[str] = None
    observed_at_iso: str

    def compute_digest(self) -> str:
        return sha256_digest(self)


class CompensationReceiptV1(BaseModel):
    contract_version: str = VERITAS_CONTRACT_VERSION
    receipt_id: str
    device_id: str
    boot_epoch: str
    target_entry_digest: str
    compensation_action_digest: str
    status: CompensationStatus
    observed_output: Dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
    recorded_at_iso: str

    def compute_digest(self) -> str:
        return sha256_digest(self)


class ReconciliationReceiptV1(BaseModel):
    contract_version: str = VERITAS_CONTRACT_VERSION
    receipt_id: str
    device_id: str
    boot_epoch: str
    package_digest: str
    acknowledged_tail_digest: str
    remote_receipt_digest: str
    reconciled_at_iso: str

    def compute_digest(self) -> str:
        return sha256_digest(self)


class VeritasRecordV1(BaseModel):
    contract_version: str = VERITAS_CONTRACT_VERSION
    record_type: VeritasRecordType
    device_id: str
    boot_epoch: str
    payload: Dict[str, Any]
    payload_digest: str
    recorded_at_iso: str

    def compute_digest(self) -> str:
        return sha256_digest(self)


class VeritasChainEntryV1(BaseModel):
    contract_version: str = VERITAS_CONTRACT_VERSION
    sequence: int = Field(ge=0)
    previous_entry_digest: str
    record: VeritasRecordV1
    entry_digest: Optional[str] = None

    def digest_payload(self) -> Dict[str, Any]:
        return self.model_dump(
            mode="json",
            exclude={"entry_digest"},
            exclude_none=True,
        )

    def compute_digest(self) -> str:
        return sha256_digest(self.digest_payload())

    def model_post_init(self, __context: Any) -> None:
        if self.entry_digest is None:
            self.entry_digest = self.compute_digest()


class VeritasEdgeStateV1(BaseModel):
    state_version: str = "valo.edge.veritas-state.v1"
    next_sequence: int = Field(default=0, ge=0)
    tail_digest: str = VERITAS_GENESIS_DIGEST
    current_boot_epoch: Optional[str] = None

    def compute_digest(self) -> str:
        return sha256_digest(self)


class EdgeEvidencePackageV1(BaseModel):
    contract_version: str = VERITAS_CONTRACT_VERSION
    package_id: str
    device_id: str
    from_sequence: int = Field(ge=0)
    to_sequence: int = Field(ge=0)
    starting_previous_digest: str
    ending_digest: str
    entries: List[VeritasChainEntryV1]
    exported_at_iso: str
    package_digest: Optional[str] = None
    attestation: Optional[SignatureV1] = None

    def digest_payload(self) -> Dict[str, Any]:
        return self.model_dump(
            mode="json",
            exclude={"package_digest", "attestation"},
            exclude_none=True,
        )

    def compute_digest(self) -> str:
        return sha256_digest(self.digest_payload())

    def model_post_init(self, __context: Any) -> None:
        if self.package_digest is None:
            self.package_digest = self.compute_digest()


__all__ = [
    "AuthorizationReceiptV1",
    "BootContinuityReceiptV1",
    "CompensationReceiptV1",
    "CompensationStatus",
    "ConsequenceEvidenceState",
    "EdgeEvidencePackageV1",
    "EnforcementReceiptV1",
    "ExecutionObservationReceiptV1",
    "ReconciliationReceiptV1",
    "VERITAS_CONTRACT_VERSION",
    "VERITAS_GENESIS_DIGEST",
    "VeritasChainEntryV1",
    "VeritasEdgeStateV1",
    "VeritasRecordType",
    "VeritasRecordV1",
]
