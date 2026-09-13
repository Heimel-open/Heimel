"""Deterministic authority, policy, permit and state contracts for micro-REHT V1."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from valo_edge.contracts import SignatureV1, sha256_digest


AUTHORITY_CONTRACT_VERSION = "valo.edge.authority.v1"


class ParameterValueType(str, Enum):
    NUMBER = "NUMBER"
    INTEGER = "INTEGER"
    STRING = "STRING"
    BOOLEAN = "BOOLEAN"
    OBJECT = "OBJECT"


class ParameterRuleV1(BaseModel):
    required: bool = True
    value_type: Optional[ParameterValueType] = None
    minimum: Optional[float] = None
    maximum: Optional[float] = None
    allowed_values: Optional[List[Any]] = None


class StatePredicateOperator(str, Enum):
    EQ = "EQ"
    NE = "NE"
    LT = "LT"
    LTE = "LTE"
    GT = "GT"
    GTE = "GTE"
    IN = "IN"
    NOT_IN = "NOT_IN"


class StatePredicateV1(BaseModel):
    path: str
    operator: StatePredicateOperator
    expected: Any


class AuthorityBudgetV1(BaseModel):
    max_uses: int = Field(default=1, ge=1)
    max_actions_per_window: Optional[int] = Field(default=None, ge=1)
    window_seconds: Optional[int] = Field(default=None, ge=1)
    max_energy_j: Optional[float] = Field(default=None, ge=0)
    energy_parameter: str = "energy_j"
    max_duration_ms: Optional[int] = Field(default=None, ge=0)
    duration_parameter: str = "duration_ms"
    max_value: Optional[float] = Field(default=None, ge=0)
    value_parameter: str = "value"
    permit_uses: int = Field(default=1, ge=1)


class OfflineAuthorityEnvelopeV1(BaseModel):
    contract_version: str = AUTHORITY_CONTRACT_VERSION
    envelope_id: str
    device_id: str
    allowed_action_types: List[str]
    parameter_rules: Dict[str, ParameterRuleV1] = Field(default_factory=dict)
    allow_unruled_parameters: bool = False
    required_model_hash: Optional[str] = None
    required_firmware_hash: str
    required_runtime_hash: str
    max_freshness_ms: int = Field(default=60_000, ge=0)
    required_sensor_sources: List[str] = Field(default_factory=list)
    state_predicates: List[StatePredicateV1] = Field(default_factory=list)
    budgets: AuthorityBudgetV1 = Field(default_factory=AuthorityBudgetV1)
    valid_from_iso: str
    valid_until_iso: str
    revoked: bool = False
    signer_key_id: str
    signature: Optional[SignatureV1] = None

    def signed_payload(self) -> Dict[str, Any]:
        return self.model_dump(mode="json", exclude={"signature"}, exclude_none=True)

    def compute_digest(self) -> str:
        return sha256_digest(self.signed_payload())


class PermitStateV1(BaseModel):
    permit_id: str
    envelope_id: str
    proposal_digest: str
    remaining_uses: int = Field(ge=0)


class MicroRehtStateV1(BaseModel):
    state_version: str = "valo.edge.micro-reht-state.v1"
    seen_nonce_digests: Dict[str, str] = Field(default_factory=dict)
    last_sequence_by_boot: Dict[str, int] = Field(default_factory=dict)
    envelope_use_count: Dict[str, int] = Field(default_factory=dict)
    envelope_action_times: Dict[str, List[str]] = Field(default_factory=dict)
    envelope_energy_used: Dict[str, float] = Field(default_factory=dict)
    envelope_value_used: Dict[str, float] = Field(default_factory=dict)
    issued_permits: Dict[str, PermitStateV1] = Field(default_factory=dict)
    halted: bool = False
    halt_reason: str = ""
    halt_at_iso: Optional[str] = None

    def compute_digest(self) -> str:
        return sha256_digest(self)
