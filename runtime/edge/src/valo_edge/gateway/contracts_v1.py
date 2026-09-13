"""Versioned mechanical enforcement contracts for VALO Edge."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field

from valo_edge.contracts import EdgeEnforcementV1, sha256_digest


class DriverExecutionStatus(str, Enum):
    EXECUTED = "EXECUTED"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    REJECTED = "REJECTED"


class DeviceCommandV1(BaseModel):
    """Exact mechanical command bound to one authorized proposal and permit use."""

    command_id: str
    proposal_digest: str
    device_id: str
    action_type: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    permit_id: str
    permit_use_index: int = Field(ge=0)
    issued_at_iso: str

    def compute_digest(self) -> str:
        return sha256_digest(self)


class DriverOutcomeV1(BaseModel):
    """What the device driver actually reported after an execution attempt."""

    status: DriverExecutionStatus
    observed_output: Dict[str, Any] = Field(default_factory=dict)
    error_code: Optional[str] = None
    error_detail: Optional[str] = None

    def compute_digest(self) -> str:
        return sha256_digest(self)


class GatewayExecutionResultV1(BaseModel):
    """Mechanical gateway result. This is not an authorization decision."""

    enforcement: EdgeEnforcementV1
    driver_outcome: DriverOutcomeV1

    def compute_digest(self) -> str:
        return sha256_digest(self)


__all__ = [
    "DeviceCommandV1",
    "DriverExecutionStatus",
    "DriverOutcomeV1",
    "GatewayExecutionResultV1",
]
