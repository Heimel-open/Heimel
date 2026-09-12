from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..types.strength import validate_type_expression
from .common import (
    AutonomyLevel,
    FunctionStatus,
    IdempotencyRequirement,
    RiskClass,
)


class TypeRef(BaseModel):
    """A typed value reference. Uses the Function Fabric type vocabulary, e.g.
    'Verified<Recipient>', 'CandidateSet<Resource>', 'Amount'."""

    name: str
    type: str

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def check_type(self) -> TypeRef:
        validate_type_expression(self.type)
        return self


class Predicate(BaseModel):
    """A deterministic boolean predicate expression (Workflow ISA syntax)."""

    expression: str

    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityRequirement(BaseModel):
    capability: str
    scope: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceRequirement(BaseModel):
    required_types: list[str] = Field(default_factory=list)
    minimum_status: str = "ADMITTED"

    model_config = ConfigDict(extra="forbid", frozen=True)


class RightsRequirement(BaseModel):
    required_rights: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)


class PurposeRequirement(BaseModel):
    purpose_types: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)


class JurisdictionRef(BaseModel):
    country: str  # e.g. "NO", "EU"
    code: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)


class AutonomyProfile(BaseModel):
    allowed_autonomy_levels: list[AutonomyLevel]
    default_autonomy_level: AutonomyLevel

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def check_default_allowed(self) -> AutonomyProfile:
        if self.default_autonomy_level not in self.allowed_autonomy_levels:
            raise ValueError("default_autonomy_level must be in allowed_autonomy_levels")
        return self


class FunctionDefinition(BaseModel):
    """Canonical Function contract. A Function is a versioned, typed program.
    Frozen; `extra="forbid"`."""

    function_id: str  # machine-readable identity, e.g. "valo.finance.pay"
    name: str
    version: str  # e.g. "1.0.0"

    input_type: TypeRef
    output_type: TypeRef

    workflow_ref: str  # WorkflowGraph id (registered graph id + version)

    preconditions: list[Predicate] = Field(default_factory=list)
    postconditions: list[Predicate] = Field(default_factory=list)

    effects: list[str] = Field(default_factory=list)  # Workflow ISA EffectType values
    risk_class: RiskClass = RiskClass.R0_INFORMATIONAL
    autonomy_profile: AutonomyProfile

    authority_requirements: list[AuthorityRequirement] = Field(default_factory=list)
    evidence_requirements: list[EvidenceRequirement] = Field(default_factory=list)
    rights_requirements: list[RightsRequirement] = Field(default_factory=list)
    purpose_requirements: list[PurposeRequirement] = Field(default_factory=list)

    jurisdiction_constraints: list[JurisdictionRef] = Field(default_factory=list)

    reversible: bool = False
    idempotency_requirement: IdempotencyRequirement = IdempotencyRequirement.NONE

    deprecated: bool = False
    status: FunctionStatus = FunctionStatus.DRAFT
    economic_profile_ref: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    def identity(self) -> str:
        return f"{self.function_id}@{self.version}"

    @model_validator(mode="after")
    def check_identity(self) -> FunctionDefinition:
        if not self.function_id or "@" in self.function_id:
            raise ValueError("function_id must be a machine-readable id without '@'")
        if not self.version:
            raise ValueError("version is required")
        if self.deprecated and self.status != FunctionStatus.DEPRECATED:
            return self.model_copy(update={"status": FunctionStatus.DEPRECATED})
        return self

