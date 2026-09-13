"""Canonical contracts for VALO Edge (Tiny Edge Profile)."""

from enum import Enum
import hashlib
import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class EdgeDecision(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    DEFER = "DEFER"
    STEP_UP = "STEP_UP"
    HALT = "HALT"


_DERIVED_HASH_FIELDS = {
    "proposal_hash",
    "authority_digest",
    "decision_digest",
    "receipt_digest",
    "evidence_digest",
    "commitment_hash",
}


def _canonical_json(model: BaseModel) -> str:
    data = model.model_dump(mode="json")
    for field in _DERIVED_HASH_FIELDS:
        data.pop(field, None)
    return json.dumps(
        data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def _stable_hash(model: BaseModel) -> str:
    return hashlib.sha256(_canonical_json(model).encode("utf-8")).hexdigest()


class EdgeActionProposal(BaseModel):
    """Proposal emitted by local models or sensor triggers. Not executable directly."""
    proposal_id: str
    device_id: str
    action_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    timestamp_iso: str
    nonce: str
    boot_epoch: str = ""
    sequence: int = 0
    key_id: str = ""
    signature: str = ""
    model_manifest_hash: str = ""
    firmware_hash: str = ""
    sensor_digest: str = ""
    device_attestation_hash: str = ""
    evidence_digest: str = ""
    physical_state: Dict[str, Any] = Field(default_factory=dict)
    proposal_hash: Optional[str] = None

    def compute_hash(self) -> str:
        return _stable_hash(self)

    def model_post_init(self, __context: Any) -> None:
        if not self.proposal_hash:
            self.proposal_hash = self.compute_hash()


class OfflineAuthorityEnvelope(BaseModel):
    """Signed authority limits governing offline micro-REHT decisions."""
    envelope_id: str
    device_id: str
    allowed_action_types: List[str]
    max_rate_per_sec: float = 10.0
    valid_until_iso: str
    valid_from_iso: str = ""
    is_revoked: bool = False
    key_id: str = ""
    boot_epoch: str = ""
    version: str = "1"
    policy_version: str = ""
    authority_digest: Optional[str] = None

    def compute_digest(self) -> str:
        return _stable_hash(self)

    def model_post_init(self, __context: Any) -> None:
        if not self.authority_digest:
            self.authority_digest = self.compute_digest()


class EdgeClearance(BaseModel):
    """Deterministic clearance decision produced by micro-REHT."""
    clearance_id: str
    proposal_id: str
    decision: EdgeDecision
    reason: str
    envelope_id: Optional[str] = None
    timestamp_iso: str
    decision_digest: Optional[str] = None

    def compute_digest(self) -> str:
        return _stable_hash(self)

    def model_post_init(self, __context: Any) -> None:
        if not self.decision_digest:
            self.decision_digest = self.compute_digest()


class EdgeExecutionReceipt(BaseModel):
    """Veritas receipt recording executed or denied device action."""
    receipt_id: str
    proposal_id: str
    clearance_id: str
    device_id: str
    decision: EdgeDecision
    executed: bool
    timestamp_iso: str
    receipt_digest: Optional[str] = None

    def compute_digest(self) -> str:
        return _stable_hash(self)

    def model_post_init(self, __context: Any) -> None:
        if not self.receipt_digest:
            self.receipt_digest = self.compute_digest()


class EdgeEvidenceEnvelope(BaseModel):
    """Sensor, hardware, model and runtime evidence bound to a proposal."""
    evidence_id: str
    proposal_id: str
    device_attestation_hash: str = ""
    model_manifest_hash: str = ""
    firmware_hash: str = ""
    sensor_digest: str = ""
    physical_state: Dict[str, Any] = Field(default_factory=dict)
    evidence_age_seconds: Optional[float] = None
    evidence_digest: Optional[str] = None

    def compute_digest(self) -> str:
        return _stable_hash(self)

    def model_post_init(self, __context: Any) -> None:
        if not self.evidence_digest:
            self.evidence_digest = self.compute_digest()


class EdgeCommitmentV1(BaseModel):
    """Versioned commitment binding proposal, evidence, envelope and clearance."""
    commitment_id: str
    proposal: EdgeActionProposal
    evidence: EdgeEvidenceEnvelope
    envelope: OfflineAuthorityEnvelope
    clearance: Optional[EdgeClearance] = None
    receipt: Optional[EdgeExecutionReceipt] = None
    commitment_hash: Optional[str] = None

    def compute_digest(self) -> str:
        return _stable_hash(self)

    def model_post_init(self, __context: Any) -> None:
        if not self.commitment_hash:
            self.commitment_hash = self.compute_digest()
