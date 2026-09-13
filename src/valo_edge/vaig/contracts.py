"""Structured evidence inputs and assessments for Local VAIG Edge."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from valo_edge.contracts import EdgeEvidenceV1, sha256_digest


class EvidenceGapSeverity(str, Enum):
    MISSING = "MISSING"
    STALE = "STALE"
    CONTRADICTORY = "CONTRADICTORY"
    UNTRUSTED = "UNTRUSTED"


class EvidenceGapV1(BaseModel):
    field: str
    severity: EvidenceGapSeverity
    reason: str


class EvidenceRequirementsV1(BaseModel):
    require_device_attestation: bool = True
    require_firmware_hash: bool = True
    require_runtime_hash: bool = True
    require_model: bool = False
    min_sensor_sources: int = Field(default=1, ge=0)
    max_freshness_ms: int = Field(default=60_000, ge=0)
    required_state_keys: List[str] = Field(default_factory=list)
    expected_state: Dict[str, Any] = Field(default_factory=dict)

    def compute_digest(self) -> str:
        return sha256_digest(self)


class DeviceAttestationEvidenceV1(BaseModel):
    device_id: str
    hardware_attestation_hash: str = ""
    firmware_hash: str = ""
    runtime_hash: str = ""
    boot_epoch: str = ""
    key_id: str = ""
    revoked: bool = False

    def compute_digest(self) -> str:
        return sha256_digest(self)


class SensorEvidenceV1(BaseModel):
    source_id: str
    source_type: str
    evidence_digest: str
    observed_at_iso: str
    provenance: List[str] = Field(default_factory=list)

    def compute_digest(self) -> str:
        return sha256_digest(self)


class PhysicalStateEvidenceV1(BaseModel):
    state: Dict[str, Any] = Field(default_factory=dict)
    contradictions: List[str] = Field(default_factory=list)

    def compute_digest(self) -> str:
        return sha256_digest(self.state)


class ModelSignalV1(BaseModel):
    model_hash: str
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    uncertainty: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    calibration: str = ""

    def compute_digest(self) -> str:
        return sha256_digest(self)


class LocalVaigAssessmentV1(BaseModel):
    """VAIG output. It contains evidence and gaps, never an authorization decision."""

    evidence: EdgeEvidenceV1
    requirements_digest: str
    gaps: List[EvidenceGapV1] = Field(default_factory=list)

    def is_complete(self) -> bool:
        return self.evidence.completeness and not self.gaps

    def compute_digest(self) -> str:
        return sha256_digest(self)
