from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .actor_standing import ActorDecisionStanding, DecisionFunction, StandingDecision
from .common import canonical_digest
from .time import TimeWindow


class ConsequenceRelation(str, Enum):
    BENEFICIARY = "BENEFICIARY"
    AFFECTED_PARTY = "AFFECTED_PARTY"
    RISK_BEARER = "RISK_BEARER"
    RIGHTS_HOLDER = "RIGHTS_HOLDER"
    LIABILITY_BEARER = "LIABILITY_BEARER"
    DATA_SUBJECT = "DATA_SUBJECT"
    RESOURCE_OWNER = "RESOURCE_OWNER"


class DecisionContributionType(str, Enum):
    ASSESSMENT = "ASSESSMENT"
    RECOMMENDATION = "RECOMMENDATION"
    APPROVAL = "APPROVAL"
    AUTHORITY_GRANT = "AUTHORITY_GRANT"
    RISK_ACCEPTANCE = "RISK_ACCEPTANCE"
    VERIFICATION = "VERIFICATION"


_CONTRIBUTION_FUNCTION = {
    DecisionContributionType.ASSESSMENT: DecisionFunction.ASSESS,
    DecisionContributionType.RECOMMENDATION: DecisionFunction.RECOMMEND,
    DecisionContributionType.APPROVAL: DecisionFunction.APPROVE,
    DecisionContributionType.AUTHORITY_GRANT: DecisionFunction.AUTHORIZE,
    DecisionContributionType.RISK_ACCEPTANCE: DecisionFunction.ACCEPT_RISK,
    DecisionContributionType.VERIFICATION: DecisionFunction.VERIFY,
}


class OmissionSeverity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MATERIAL = "MATERIAL"
    CRITICAL = "CRITICAL"


class NormalPathAvailability(str, Enum):
    AVAILABLE = "AVAILABLE"
    UNAVAILABLE = "UNAVAILABLE"
    INSUFFICIENT_TIME = "INSUFFICIENT_TIME"
    DENIED = "DENIED"
    UNKNOWN = "UNKNOWN"


class Reversibility(str, Enum):
    REVERSIBLE = "REVERSIBLE"
    PARTIALLY_REVERSIBLE = "PARTIALLY_REVERSIBLE"
    IRREVERSIBLE = "IRREVERSIBLE"


class EmergencyDecision(str, Enum):
    PASS = "PASS"
    STEP_UP = "STEP_UP"
    DENY = "DENY"


class ConsequencePartyBinding(BaseModel):
    schema_version: Literal["consequence_party_binding.v1"] = (
        "consequence_party_binding.v1"
    )
    binding_id: str
    action_id: str
    party_id: str
    relation: ConsequenceRelation
    basis_ref: str
    evidence_refs: tuple[str, ...]
    evaluated_at: datetime
    valid_until: datetime

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_binding(self) -> ConsequencePartyBinding:
        if any(not value for value in (self.binding_id, self.action_id, self.party_id, self.basis_ref)):
            raise ValueError("consequence party binding fields are required")
        if not self.evidence_refs:
            raise ValueError("consequence party binding requires evidence")
        if self.valid_until <= self.evaluated_at:
            raise ValueError("consequence party binding requires positive validity")
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.evaluated_at <= moment < self.valid_until


class ConsequenceProfile(BaseModel):
    schema_version: Literal["consequence_profile.v1"] = "consequence_profile.v1"
    profile_id: str
    action_id: str
    bindings: tuple[ConsequencePartyBinding, ...]
    evaluated_at: datetime
    valid_until: datetime
    profile_digest: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"profile_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_profile(self) -> ConsequenceProfile:
        if not self.bindings:
            raise ValueError("consequence profile requires at least one party binding")
        keys = [(item.relation, item.party_id) for item in self.bindings]
        if len(set(keys)) != len(keys):
            raise ValueError("consequence party relations must be unique per party")
        if any(item.action_id != self.action_id for item in self.bindings):
            raise ValueError("consequence profile contains another action")
        if self.valid_until <= self.evaluated_at:
            raise ValueError("consequence profile requires positive validity")
        if self.valid_until > min(item.valid_until for item in self.bindings):
            raise ValueError("consequence profile outlives a party binding")
        if self.profile_digest and self.profile_digest != self.computed_digest:
            raise ValueError("consequence profile digest mismatch")
        return self


class DecisionContribution(BaseModel):
    schema_version: Literal["decision_contribution.v1"] = "decision_contribution.v1"
    contribution_id: str
    contribution_type: DecisionContributionType
    contribution_ref: str
    action_id: str
    actor_id: str
    actor_standing: ActorDecisionStanding
    issued_at: datetime
    valid_until: datetime
    contribution_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"contribution_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_contribution(self) -> DecisionContribution:
        if any(not value for value in (self.contribution_id, self.contribution_ref, self.action_id, self.actor_id)):
            raise ValueError("decision contribution fields are required")
        standing = self.actor_standing
        if standing.standing_digest != standing.computed_digest:
            raise ValueError("decision contribution standing is unsealed")
        if standing.decision is not StandingDecision.PASS:
            raise ValueError("decision contribution requires PASS actor standing")
        if standing.actor_id != self.actor_id:
            raise ValueError("decision contribution actor mismatch")
        if standing.action_id != self.action_id:
            raise ValueError("decision contribution action mismatch")
        expected_function = _CONTRIBUTION_FUNCTION[self.contribution_type]
        if standing.decision_function is not expected_function:
            raise ValueError("decision contribution function mismatch")
        if not (standing.evaluated_at <= self.issued_at < standing.valid_until):
            raise ValueError("decision contribution issued outside actor standing")
        if self.valid_until <= self.issued_at:
            raise ValueError("decision contribution requires positive validity")
        if self.valid_until > standing.valid_until:
            raise ValueError("decision contribution outlives actor standing")
        if self.contribution_digest and self.contribution_digest != self.computed_digest:
            raise ValueError("decision contribution digest mismatch")
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.issued_at <= moment < self.valid_until


class DecisionContributionRequirement(BaseModel):
    schema_version: Literal["decision_contribution_requirement.v1"] = (
        "decision_contribution_requirement.v1"
    )
    contribution_type: DecisionContributionType
    minimum_count: int = Field(default=1, ge=1)
    require_distinct_actors: bool = True
    prohibit_executor_as_contributor: bool = False

    model_config = ConfigDict(extra="forbid", frozen=True)


class DecisionContributionChain(BaseModel):
    schema_version: Literal["decision_contribution_chain.v1"] = (
        "decision_contribution_chain.v1"
    )
    chain_id: str
    action_id: str
    executor_standing: ActorDecisionStanding
    contributions: tuple[DecisionContribution, ...]
    requirements: tuple[DecisionContributionRequirement, ...]
    evaluated_at: datetime
    valid_until: datetime
    chain_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"chain_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_chain(self) -> DecisionContributionChain:
        if self.executor_standing.standing_digest != self.executor_standing.computed_digest:
            raise ValueError("executor standing is unsealed")
        if self.executor_standing.decision is not StandingDecision.PASS:
            raise ValueError("decision contribution chain requires PASS executor standing")
        if self.executor_standing.action_id != self.action_id:
            raise ValueError("executor standing action mismatch")
        if not (
            self.executor_standing.evaluated_at
            <= self.evaluated_at
            < self.executor_standing.valid_until
        ):
            raise ValueError("executor standing is not current")
        contribution_ids = [item.contribution_id for item in self.contributions]
        if len(set(contribution_ids)) != len(contribution_ids):
            raise ValueError("decision contribution IDs must be unique")
        for item in self.contributions:
            if item.action_id != self.action_id:
                raise ValueError("decision contribution chain contains another action")
            if item.contribution_digest != item.computed_digest:
                raise ValueError("decision contribution is unsealed")
            if not item.is_current(self.evaluated_at):
                raise ValueError("decision contribution is not current")
        for requirement in self.requirements:
            matching = [
                item
                for item in self.contributions
                if item.contribution_type is requirement.contribution_type
            ]
            if len(matching) < requirement.minimum_count:
                raise ValueError(
                    f"missing required decision contributions: {requirement.contribution_type.value}"
                )
            actors = [item.actor_id for item in matching]
            if requirement.require_distinct_actors and len(set(actors)) != len(actors):
                raise ValueError("required decision contributors must be distinct")
            if requirement.prohibit_executor_as_contributor and self.executor_standing.actor_id in actors:
                raise ValueError("executor cannot satisfy this decision contribution")
        if self.valid_until <= self.evaluated_at:
            raise ValueError("decision contribution chain requires positive validity")
        bounds = [
            self.executor_standing.valid_until,
            *(item.valid_until for item in self.contributions),
        ]
        if self.valid_until > min(bounds):
            raise ValueError("decision contribution chain outlives a dependency")
        if self.chain_digest and self.chain_digest != self.computed_digest:
            raise ValueError("decision contribution chain digest mismatch")
        return self


class OmissionConsequenceAssessment(BaseModel):
    schema_version: Literal["omission_consequence_assessment.v1"] = (
        "omission_consequence_assessment.v1"
    )
    assessment_id: str
    action_id: str
    severity: OmissionSeverity
    consequence_refs: tuple[str, ...] = ()
    affected_party_refs: tuple[str, ...] = ()
    trigger_deadline: datetime | None = None
    safe_null_effect: bool
    evidence_refs: tuple[str, ...]
    evaluated_at: datetime
    valid_until: datetime
    assessment_digest: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"assessment_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_assessment(self) -> OmissionConsequenceAssessment:
        if self.valid_until <= self.evaluated_at:
            raise ValueError("omission assessment requires positive validity")
        if not self.evidence_refs:
            raise ValueError("omission assessment requires evidence")
        if self.severity in {OmissionSeverity.MATERIAL, OmissionSeverity.CRITICAL}:
            if not self.consequence_refs:
                raise ValueError("material omission requires consequence references")
            if self.safe_null_effect:
                raise ValueError("material omission cannot classify null effect as safe")
        if self.assessment_digest and self.assessment_digest != self.computed_digest:
            raise ValueError("omission assessment digest mismatch")
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.evaluated_at <= moment < self.valid_until


class NormalPathAssessment(BaseModel):
    schema_version: Literal["normal_path_assessment.v1"] = "normal_path_assessment.v1"
    assessment_id: str
    action_id: str
    availability: NormalPathAvailability
    reason_refs: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    evaluated_at: datetime
    valid_until: datetime
    assessment_digest: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"assessment_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_assessment(self) -> NormalPathAssessment:
        if self.valid_until <= self.evaluated_at:
            raise ValueError("normal-path assessment requires positive validity")
        if not self.reason_refs or not self.evidence_refs:
            raise ValueError("normal-path assessment requires reasons and evidence")
        if self.assessment_digest and self.assessment_digest != self.computed_digest:
            raise ValueError("normal-path assessment digest mismatch")
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.evaluated_at <= moment < self.valid_until


class MinimumSafeResponseAssessment(BaseModel):
    schema_version: Literal["minimum_safe_response_assessment.v1"] = (
        "minimum_safe_response_assessment.v1"
    )
    assessment_id: str
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    candidate_set_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    reversibility: Reversibility
    sufficient_to_control_hazard: bool
    no_lower_impact_sufficient_action: bool
    evidence_refs: tuple[str, ...]
    evaluated_at: datetime
    valid_until: datetime
    assessment_digest: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"assessment_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_assessment(self) -> MinimumSafeResponseAssessment:
        if self.valid_until <= self.evaluated_at:
            raise ValueError("minimum-safe-response assessment requires positive validity")
        if not self.evidence_refs:
            raise ValueError("minimum-safe-response assessment requires evidence")
        if self.assessment_digest and self.assessment_digest != self.computed_digest:
            raise ValueError("minimum-safe-response assessment digest mismatch")
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.evaluated_at <= moment < self.valid_until


class EmergencyExecutorReadiness(BaseModel):
    schema_version: Literal["emergency_executor_readiness.v1"] = (
        "emergency_executor_readiness.v1"
    )
    readiness_id: str
    actor_id: str
    role_binding_id: str
    represented_principal_id: str
    decision_function: DecisionFunction
    capability: str
    jurisdiction_ref: str
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    role_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    competence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    attention_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    eligibility_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evaluated_at: datetime
    valid_until: datetime
    decision: StandingDecision
    reason_codes: tuple[str, ...]
    readiness_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"readiness_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_readiness(self) -> EmergencyExecutorReadiness:
        if self.decision_function is not DecisionFunction.EXECUTE:
            raise ValueError("emergency executor readiness must use EXECUTE function")
        if self.valid_until <= self.evaluated_at:
            raise ValueError("emergency readiness requires positive validity")
        if self.decision is StandingDecision.PASS and self.reason_codes:
            raise ValueError("PASS readiness cannot carry failure reasons")
        if self.decision is not StandingDecision.PASS and not self.reason_codes:
            raise ValueError("non-PASS readiness requires reason codes")
        if self.readiness_digest and self.readiness_digest != self.computed_digest:
            raise ValueError("emergency readiness digest mismatch")
        return self


class EmergencyConditionEvidence(BaseModel):
    schema_version: Literal["emergency_condition_evidence.v1"] = (
        "emergency_condition_evidence.v1"
    )
    condition_id: str
    mandate_id: str
    condition_ref: str
    satisfied: bool
    observed_at: datetime
    valid_until: datetime
    evidence_refs: tuple[str, ...]
    condition_digest: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"condition_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_condition(self) -> EmergencyConditionEvidence:
        if self.valid_until <= self.observed_at:
            raise ValueError("emergency condition requires positive validity")
        if not self.evidence_refs:
            raise ValueError("emergency condition requires evidence")
        if self.condition_digest and self.condition_digest != self.computed_digest:
            raise ValueError("emergency condition digest mismatch")
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.observed_at <= moment < self.valid_until


class EmergencyMandate(BaseModel):
    schema_version: Literal["emergency_mandate.v1"] = "emergency_mandate.v1"
    mandate_id: str
    represented_principal_id: str
    grantor_id: str
    grantor_standing_ref: str
    grantor_standing_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    executor_refs: tuple[str, ...]
    allowed_capabilities: tuple[str, ...]
    target_refs: tuple[str, ...]
    allowed_effects: tuple[str, ...]
    purpose_refs: tuple[str, ...]
    trigger_refs: tuple[str, ...]
    max_risk_class: str | None = None
    evidence_refs: tuple[str, ...]
    validity: TimeWindow
    revocation_registry_ref: str
    delegation_allowed: Literal[False] = False
    scope_expansion_allowed: Literal[False] = False
    self_renewal_allowed: Literal[False] = False
    denial_as_trigger_allowed: Literal[False] = False
    chaining_allowed: Literal[False] = False
    single_use_required: Literal[True] = True
    mandate_digest: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"mandate_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_mandate(self) -> EmergencyMandate:
        required = (
            self.mandate_id,
            self.represented_principal_id,
            self.grantor_id,
            self.grantor_standing_ref,
            self.revocation_registry_ref,
        )
        if any(not item for item in required):
            raise ValueError("emergency mandate identity and authority source are required")
        if not self.executor_refs:
            raise ValueError("emergency mandate requires explicit executors")
        if self.grantor_id in self.executor_refs:
            raise ValueError("emergency executor cannot issue its own mandate")
        bounded_sets = (
            self.allowed_capabilities,
            self.target_refs,
            self.allowed_effects,
            self.purpose_refs,
            self.trigger_refs,
            self.evidence_refs,
        )
        if any(not values for values in bounded_sets):
            raise ValueError("emergency mandate requires bounded non-empty scope")
        if any("*" in values for values in bounded_sets[:-1]):
            raise ValueError("emergency mandate cannot contain wildcard scope")
        if self.mandate_digest and self.mandate_digest != self.computed_digest:
            raise ValueError("emergency mandate digest mismatch")
        return self

    def is_current(self, moment: datetime) -> bool:
        return self.validity.is_active_at(moment)


class EmergencyActivation(BaseModel):
    schema_version: Literal["emergency_activation.v1"] = "emergency_activation.v1"
    activation_id: str
    action_id: str
    action_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    mandate: EmergencyMandate
    readiness: EmergencyExecutorReadiness
    omission_assessment: OmissionConsequenceAssessment
    normal_path_assessment: NormalPathAssessment
    minimum_safe_response: MinimumSafeResponseAssessment
    conditions: tuple[EmergencyConditionEvidence, ...]
    evaluated_at: datetime
    valid_until: datetime
    decision: EmergencyDecision
    reason_codes: tuple[str, ...]
    activation_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    scope_effect: Literal["ACTIVATE_PREAUTHORIZED_SCOPE_ONLY"] = (
        "ACTIVATE_PREAUTHORIZED_SCOPE_ONLY"
    )
    can_issue_clearance: Literal[False] = False
    requires_fresh_reht: Literal[True] = True
    single_use_required: Literal[True] = True

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"activation_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_activation(self) -> EmergencyActivation:
        if self.valid_until <= self.evaluated_at:
            raise ValueError("emergency activation requires positive validity")
        if self.decision is EmergencyDecision.PASS and self.reason_codes:
            raise ValueError("PASS emergency activation cannot carry failure reasons")
        if self.decision is not EmergencyDecision.PASS and not self.reason_codes:
            raise ValueError("non-PASS emergency activation requires reason codes")
        if self.mandate.mandate_digest != self.mandate.computed_digest:
            raise ValueError("emergency mandate is unsealed")
        if self.readiness.readiness_digest != self.readiness.computed_digest:
            raise ValueError("emergency readiness is unsealed")
        if self.omission_assessment.assessment_digest != self.omission_assessment.computed_digest:
            raise ValueError("omission assessment is unsealed")
        if self.normal_path_assessment.assessment_digest != self.normal_path_assessment.computed_digest:
            raise ValueError("normal-path assessment is unsealed")
        if self.minimum_safe_response.assessment_digest != self.minimum_safe_response.computed_digest:
            raise ValueError("minimum-safe-response assessment is unsealed")
        if any(item.condition_digest != item.computed_digest for item in self.conditions):
            raise ValueError("emergency condition is unsealed")
        if self.activation_digest and self.activation_digest != self.computed_digest:
            raise ValueError("emergency activation digest mismatch")
        return self
