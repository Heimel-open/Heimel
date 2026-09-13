"""Versioned canonical contracts for VALO Edge consequences.

These objects keep proposal, evidence, clearance, enforcement and observation
separate. Digests use canonical UTF-8 JSON so other runtimes can reproduce the
same commitment bytes.
"""

from __future__ import annotations

from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


CONTRACT_VERSION = "valo.edge.contracts.v1"


def canonical_json_bytes(value: Any) -> bytes:
    if isinstance(value, BaseModel):
        value = value.model_dump(mode="json", exclude_none=True)
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def sha256_digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()


class ConsequenceDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    DEFER = "DEFER"
    STEP_UP = "STEP_UP"
    HALT = "HALT"


class SignatureV1(BaseModel):
    algorithm: str
    key_id: str
    signature: str


class EdgeActionCommitmentV1(BaseModel):
    contract_version: str = CONTRACT_VERSION
    proposal_id: str
    device_id: str
    action_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    model_hash: str
    firmware_hash: str
    runtime_hash: str
    sensor_evidence_digest: str
    physical_state_digest: str
    authority_envelope_digest: str
    boot_epoch: str
    sequence: int = Field(ge=0)
    nonce: str
    issued_at_iso: str
    valid_until_iso: str
    signer_key_id: str
    signature: Optional[SignatureV1] = None

    def commitment_payload(self) -> Dict[str, Any]:
        return self.model_dump(mode="json", exclude={"signature"}, exclude_none=True)

    def compute_digest(self) -> str:
        return sha256_digest(self.commitment_payload())


class EdgeEvidenceV1(BaseModel):
    contract_version: str = CONTRACT_VERSION
    evidence_id: str
    proposal_digest: str
    device_attestation_digest: str
    model_hash: str
    firmware_hash: str
    runtime_hash: str
    sensor_sources: List[str] = Field(default_factory=list)
    observed_state: Dict[str, Any] = Field(default_factory=dict)
    observed_at_iso: str
    freshness_ms: int = Field(ge=0)
    completeness: bool
    contradictions: List[str] = Field(default_factory=list)
    producer_id: str
    signature: Optional[SignatureV1] = None

    def compute_digest(self) -> str:
        payload = self.model_dump(mode="json", exclude={"signature"}, exclude_none=True)
        return sha256_digest(payload)


class EdgeClearanceV1(BaseModel):
    contract_version: str = CONTRACT_VERSION
    clearance_id: str
    proposal_digest: str
    evidence_digest: str
    authority_envelope_digest: str
    decision: ConsequenceDecision
    reason_codes: List[str]
    issued_at_iso: str
    valid_until_iso: str
    boot_epoch: str
    sequence: int = Field(ge=0)
    permit_id: Optional[str] = None
    permit_uses: int = Field(default=0, ge=0)
    signer_key_id: str
    signature: Optional[SignatureV1] = None

    def compute_digest(self) -> str:
        payload = self.model_dump(mode="json", exclude={"signature"}, exclude_none=True)
        return sha256_digest(payload)


class EdgeEnforcementV1(BaseModel):
    contract_version: str = CONTRACT_VERSION
    enforcement_id: str
    proposal_digest: str
    clearance_digest: str
    device_command_digest: str
    permit_id: Optional[str] = None
    permit_use_index: Optional[int] = Field(default=None, ge=0)
    accepted: bool
    gateway_id: str
    enforced_at_iso: str

    def compute_digest(self) -> str:
        return sha256_digest(self)


class EdgeObservationV1(BaseModel):
    contract_version: str = CONTRACT_VERSION
    observation_id: str
    enforcement_digest: str
    device_id: str
    outcome: str
    observed_output: Dict[str, Any] = Field(default_factory=dict)
    observed_at_iso: str
    previous_receipt_digest: Optional[str] = None

    def compute_digest(self) -> str:
        return sha256_digest(self)
