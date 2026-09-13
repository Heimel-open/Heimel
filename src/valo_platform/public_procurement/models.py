from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..memory_provider import canonical_digest


SCHEMA_VERSION = "0.1.0"
Digest = str


class ProcurementContract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["0.1.0"] = SCHEMA_VERSION


class Money(ProcurementContract):
    amount: Decimal = Field(ge=0, max_digits=24, decimal_places=6)
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class MoneyDelta(ProcurementContract):
    amount: Decimal = Field(max_digits=24, decimal_places=6)
    currency: str = Field(pattern=r"^[A-Z]{3}$")


class EvidenceReference(ProcurementContract):
    evidence_id: str = Field(min_length=1)
    evidence_type: str = Field(min_length=1)
    source_ref: str = Field(min_length=1)
    content_digest: Digest = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    issued_at: datetime
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def expiry_follows_issue(self) -> "EvidenceReference":
        if self.expires_at is not None and self.expires_at <= self.issued_at:
            raise ValueError("expires_at must be later than issued_at")
        return self


class AuthorityBinding(ProcurementContract):
    principal_id: str = Field(min_length=1)
    mandate_ref: str = Field(min_length=1)
    delegation_ref: str | None = None
    authority_version: str = Field(min_length=1)
    valid_at: datetime
    evidence_refs: tuple[str, ...] = ()
    grants_authority: bool = False

    @model_validator(mode="after")
    def binding_is_evidence_not_authority(self) -> "AuthorityBinding":
        if self.grants_authority:
            raise ValueError("authority binding cannot create authority")
        return self


class ProcedureType(str, Enum):
    OPEN = "open"
    RESTRICTED = "restricted"
    NEGOTIATED = "negotiated"
    COMPETITIVE_DIALOGUE = "competitive_dialogue"
    INNOVATION_PARTNERSHIP = "innovation_partnership"
    DYNAMIC_SIMPLIFIED = "dynamic_simplified"
    EMERGENCY = "emergency"


class ProcedureStatus(str, Enum):
    PLANNED = "planned"
    PUBLISHED = "published"
    EVALUATING = "evaluating"
    AWARDED = "awarded"
    CONTRACTED = "contracted"
    CANCELLED = "cancelled"
    CLOSED = "closed"


class EligibilityStatus(str, Enum):
    ELIGIBLE = "eligible"
    INELIGIBLE = "ineligible"
    EXCLUDED = "excluded"
    INCOMPLETE = "incomplete"
    EXPIRED = "expired"


class AwardStatus(str, Enum):
    PROPOSED = "proposed"
    CLEARED = "cleared"
    COMMITTED = "committed"
    REVOKED = "revoked"


class ContractStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    EXPIRED = "expired"
    COMPLETED = "completed"


class ModificationKind(str, Enum):
    SCOPE = "scope"
    VALUE = "value"
    TERM = "term"
    SUPPLIER = "supplier"
    SUBCONTRACTOR = "subcontractor"
    TECHNICAL = "technical"


class SupplierChangeKind(str, Enum):
    MASTER_DATA = "master_data"
    BANK_DETAILS = "bank_details"
    OWNERSHIP_CONTROL = "ownership_control"
    SUBCONTRACTOR = "subcontractor"
    DATA_LOCATION = "data_location"


class PaymentActionKind(str, Enum):
    APPROVE = "approve"
    HOLD = "hold"
    RELEASE = "release"
    REJECT = "reject"
    EXECUTE = "execute"


class PerformanceStatus(str, Enum):
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BREACHED = "breached"
    COMPLETED = "completed"


class PublicationEventKind(str, Enum):
    NEEDS_PLAN = "needs_plan"
    NOTICE = "notice"
    AWARD = "award"
    CONTRACT = "contract"
    MODIFICATION = "modification"
    PAYMENT = "payment"
    PERFORMANCE = "performance"
    TERMINATION = "termination"


class CommitActionType(str, Enum):
    PUBLISH_NEEDS_PLAN = "publish_needs_plan"
    APPROVE_CRITERIA = "approve_criteria"
    ACCEPT_SHORTLIST = "accept_shortlist"
    EXCLUDE_OPERATOR = "exclude_operator"
    REINSTATE_OPERATOR = "reinstate_operator"
    COMMIT_AWARD = "commit_award"
    SIGN_CONTRACT = "sign_contract"
    MODIFY_CONTRACT = "modify_contract"
    CHANGE_SUPPLIER = "change_supplier"
    APPROVE_PAYMENT = "approve_payment"
    HOLD_PAYMENT = "hold_payment"
    RELEASE_PAYMENT = "release_payment"
    REJECT_PAYMENT = "reject_payment"
    EXECUTE_PAYMENT = "execute_payment"
    TERMINATE_CONTRACT = "terminate_contract"
    RENEW_CONTRACT = "renew_contract"
    EXTEND_CONTRACT = "extend_contract"
    INVOKE_EMERGENCY_PROCEDURE = "invoke_emergency_procedure"
    PUBLISH_LIFECYCLE_DATA = "publish_lifecycle_data"


class RequestedExternalCommit(ProcurementContract):
    action_type: CommitActionType
    target_system: str = Field(min_length=1)
    resource_ref: str = Field(min_length=1)
    payload_digest: Digest = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    idempotency_key: str = Field(min_length=1)
    reversible: bool
    consequence: str = Field(min_length=1)


class NeedsPlan(ProcurementContract):
    needs_plan_id: str = Field(min_length=1)
    buyer_id: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    business_need: str = Field(min_length=1)
    estimated_value: Money
    planned_publication_at: datetime | None = None
    policy_version: str = Field(min_length=1)
    evidence_refs: tuple[EvidenceReference, ...] = ()


class ProcurementProcedure(ProcurementContract):
    procedure_id: str = Field(min_length=1)
    buyer_id: str = Field(min_length=1)
    needs_plan_ref: str = Field(min_length=1)
    procedure_type: ProcedureType
    status: ProcedureStatus
    title: str = Field(min_length=1)
    created_at: datetime
    policy_version: str = Field(min_length=1)


class EconomicOperator(ProcurementContract):
    operator_id: str = Field(min_length=1)
    legal_name: str = Field(min_length=1)
    registration_country: str = Field(pattern=r"^[A-Z]{2}$")
    registration_id: str = Field(min_length=1)
    ownership_control_countries: tuple[str, ...] = ()
    eea_established: bool
    data_residency_regions: tuple[str, ...] = ()
    evidence_refs: tuple[EvidenceReference, ...] = ()


class EligibilityEvidence(ProcurementContract):
    eligibility_id: str = Field(min_length=1)
    operator_ref: str = Field(min_length=1)
    criterion_code: str = Field(min_length=1)
    status: EligibilityStatus
    assessed_at: datetime
    expires_at: datetime | None = None
    evidence_refs: tuple[EvidenceReference, ...]

    @model_validator(mode="after")
    def expiry_follows_assessment(self) -> "EligibilityEvidence":
        if self.expires_at is not None and self.expires_at <= self.assessed_at:
            raise ValueError("expires_at must be later than assessed_at")
        return self


class Tender(ProcurementContract):
    tender_id: str = Field(min_length=1)
    procedure_ref: str = Field(min_length=1)
    operator_ref: str = Field(min_length=1)
    submitted_at: datetime
    original_language: str = Field(min_length=2)
    source_digest: Digest = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    price: Money
    evidence_refs: tuple[EvidenceReference, ...] = ()


class EvaluationCriterion(ProcurementContract):
    criterion_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    weight_percent: Decimal = Field(ge=0, le=100, max_digits=6, decimal_places=3)
    quality_criterion: bool
    policy_version: str = Field(min_length=1)


class CriterionScore(ProcurementContract):
    criterion_ref: str = Field(min_length=1)
    raw_score: Decimal = Field(ge=0, le=100, max_digits=6, decimal_places=3)
    weighted_score: Decimal = Field(ge=0, le=100, max_digits=6, decimal_places=3)
    evidence_refs: tuple[str, ...] = ()


class EvaluationResult(ProcurementContract):
    evaluation_id: str = Field(min_length=1)
    tender_ref: str = Field(min_length=1)
    criterion_scores: tuple[CriterionScore, ...]
    total_score: Decimal = Field(ge=0, le=100, max_digits=6, decimal_places=3)
    evaluator_refs: tuple[str, ...]
    judge_version: str | None = None
    ambiguity_score: Decimal = Field(default=Decimal("0"), ge=0, le=1)
    evaluated_at: datetime
    grants_authority: bool = False

    @model_validator(mode="after")
    def evaluation_cannot_authorize(self) -> "EvaluationResult":
        if self.grants_authority:
            raise ValueError("evaluation result cannot grant procurement authority")
        if not self.criterion_scores:
            raise ValueError("criterion_scores cannot be empty")
        if not self.evaluator_refs:
            raise ValueError("evaluator_refs cannot be empty")
        return self


class AwardRecommendation(ProcurementContract):
    recommendation_id: str = Field(min_length=1)
    procedure_ref: str = Field(min_length=1)
    recommended_tender_ref: str = Field(min_length=1)
    evaluation_refs: tuple[str, ...]
    reason: str = Field(min_length=1)
    created_at: datetime
    grants_authority: bool = False

    @model_validator(mode="after")
    def recommendation_cannot_authorize(self) -> "AwardRecommendation":
        if self.grants_authority:
            raise ValueError("award recommendation cannot grant authority")
        if not self.evaluation_refs:
            raise ValueError("evaluation_refs cannot be empty")
        return self


class AwardDecision(ProcurementContract):
    award_decision_id: str = Field(min_length=1)
    procedure_ref: str = Field(min_length=1)
    winning_tender_ref: str = Field(min_length=1)
    status: AwardStatus
    authority: AuthorityBinding
    clearance_ref: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    decided_at: datetime
    requested_commit: RequestedExternalCommit

    @model_validator(mode="after")
    def commit_type_is_award(self) -> "AwardDecision":
        if self.requested_commit.action_type != CommitActionType.COMMIT_AWARD:
            raise ValueError("award decision requires commit_award action")
        return self


class PublicContract(ProcurementContract):
    contract_id: str = Field(min_length=1)
    award_decision_ref: str = Field(min_length=1)
    buyer_id: str = Field(min_length=1)
    operator_ref: str = Field(min_length=1)
    signed_at: datetime
    starts_at: datetime
    ends_at: datetime | None = None
    value: Money
    status: ContractStatus
    terms_digest: Digest = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def contract_dates_are_ordered(self) -> "PublicContract":
        if self.ends_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class ContractModification(ProcurementContract):
    modification_id: str = Field(min_length=1)
    contract_ref: str = Field(min_length=1)
    kind: ModificationKind
    requested_at: datetime
    value_delta: MoneyDelta | None = None
    rationale: str = Field(min_length=1)
    evidence_refs: tuple[EvidenceReference, ...] = ()
    authority: AuthorityBinding
    clearance_ref: str = Field(min_length=1)
    requested_commit: RequestedExternalCommit

    @model_validator(mode="after")
    def commit_type_is_modification(self) -> "ContractModification":
        if self.requested_commit.action_type != CommitActionType.MODIFY_CONTRACT:
            raise ValueError("contract modification requires modify_contract action")
        return self


class SupplierChange(ProcurementContract):
    supplier_change_id: str = Field(min_length=1)
    contract_ref: str = Field(min_length=1)
    change_kind: SupplierChangeKind
    previous_ref: str | None = None
    proposed_ref: str = Field(min_length=1)
    evidence_refs: tuple[EvidenceReference, ...]
    authority: AuthorityBinding
    clearance_ref: str = Field(min_length=1)
    requested_commit: RequestedExternalCommit

    @model_validator(mode="after")
    def commit_type_is_supplier_change(self) -> "SupplierChange":
        if self.requested_commit.action_type != CommitActionType.CHANGE_SUPPLIER:
            raise ValueError("supplier change requires change_supplier action")
        return self


class Invoice(ProcurementContract):
    invoice_id: str = Field(min_length=1)
    contract_ref: str = Field(min_length=1)
    operator_ref: str = Field(min_length=1)
    amount: Money
    issued_at: datetime
    due_at: datetime
    invoice_digest: Digest = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    evidence_refs: tuple[EvidenceReference, ...] = ()

    @model_validator(mode="after")
    def due_date_follows_issue(self) -> "Invoice":
        if self.due_at < self.issued_at:
            raise ValueError("due_at cannot be earlier than issued_at")
        return self


class PaymentAction(ProcurementContract):
    payment_action_id: str = Field(min_length=1)
    invoice_ref: str = Field(min_length=1)
    action_kind: PaymentActionKind
    amount: Money
    bank_account_ref: str = Field(min_length=1)
    authority: AuthorityBinding
    clearance_ref: str = Field(min_length=1)
    requested_commit: RequestedExternalCommit

    @model_validator(mode="after")
    def commit_type_matches_payment_action(self) -> "PaymentAction":
        expected = {
            PaymentActionKind.APPROVE: CommitActionType.APPROVE_PAYMENT,
            PaymentActionKind.HOLD: CommitActionType.HOLD_PAYMENT,
            PaymentActionKind.RELEASE: CommitActionType.RELEASE_PAYMENT,
            PaymentActionKind.REJECT: CommitActionType.REJECT_PAYMENT,
            PaymentActionKind.EXECUTE: CommitActionType.EXECUTE_PAYMENT,
        }[self.action_kind]
        if self.requested_commit.action_type != expected:
            raise ValueError(f"payment action {self.action_kind.value} requires {expected.value} action")
        return self


class PerformanceMetric(ProcurementContract):
    metric_id: str = Field(min_length=1)
    measured_value: Decimal
    target_value: Decimal | None = None
    unit: str = Field(min_length=1)
    evidence_refs: tuple[str, ...] = ()


class PerformanceOutcome(ProcurementContract):
    outcome_id: str = Field(min_length=1)
    contract_ref: str = Field(min_length=1)
    measured_at: datetime
    status: PerformanceStatus
    metrics: tuple[PerformanceMetric, ...]
    evidence_refs: tuple[EvidenceReference, ...] = ()


class ProcurementPublicationEvent(ProcurementContract):
    publication_event_id: str = Field(min_length=1)
    event_kind: PublicationEventKind
    object_ref: str = Field(min_length=1)
    target_schema_ref: str = Field(min_length=1)
    payload_digest: Digest = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    authority: AuthorityBinding
    clearance_ref: str = Field(min_length=1)
    requested_commit: RequestedExternalCommit
    occurred_at: datetime

    @model_validator(mode="after")
    def commit_type_is_publication(self) -> "ProcurementPublicationEvent":
        if self.requested_commit.action_type != CommitActionType.PUBLISH_LIFECYCLE_DATA:
            raise ValueError("publication event requires publish_lifecycle_data action")
        return self


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ProcurementActionCase(ProcurementContract):
    case_id: str = Field(min_length=1)
    action_ref: str = Field(min_length=1)
    purpose: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    mandate_ref: str = Field(min_length=1)
    authority: AuthorityBinding
    procedure_ref: str = Field(min_length=1)
    contract_ref: str | None = None
    operator_ref: str | None = None
    policy_version: str = Field(min_length=1)
    criteria_versions: tuple[str, ...] = ()
    evidence_refs: tuple[EvidenceReference, ...]
    current_state_digest: Digest = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    risk_level: RiskLevel
    reversible: bool
    consequence: str = Field(min_length=1)
    requested_commit: RequestedExternalCommit
    created_at: datetime
    grants_authority: bool = False
    case_digest: Digest = Field(pattern=r"^sha256:[0-9a-f]{64}$")

    @model_validator(mode="after")
    def preserve_action_clearance_boundary(self) -> "ProcurementActionCase":
        if self.grants_authority:
            raise ValueError("procurement action case cannot grant authority")
        if self.authority.principal_id != self.principal_id:
            raise ValueError("authority principal must match action case principal")
        if self.authority.mandate_ref != self.mandate_ref:
            raise ValueError("authority mandate must match action case mandate")
        expected = procurement_action_case_digest(self)
        if self.case_digest != expected:
            raise ValueError("case_digest does not match canonical action case payload")
        return self


def procurement_action_case_digest(action_case: ProcurementActionCase) -> str:
    return canonical_digest(action_case.model_dump(mode="json", exclude={"case_digest"}))


def build_procurement_action_case(**values: Any) -> ProcurementActionCase:
    provisional = ProcurementActionCase.model_construct(
        schema_version=SCHEMA_VERSION,
        grants_authority=False,
        case_digest="sha256:" + "0" * 64,
        **values,
    )
    digest = procurement_action_case_digest(provisional)
    return ProcurementActionCase(**values, grants_authority=False, case_digest=digest)


PUBLIC_PROCUREMENT_MODELS: tuple[type[BaseModel], ...] = (
    Money,
    MoneyDelta,
    EvidenceReference,
    AuthorityBinding,
    RequestedExternalCommit,
    NeedsPlan,
    ProcurementProcedure,
    EconomicOperator,
    EligibilityEvidence,
    Tender,
    EvaluationCriterion,
    CriterionScore,
    EvaluationResult,
    AwardRecommendation,
    AwardDecision,
    PublicContract,
    ContractModification,
    SupplierChange,
    Invoice,
    PaymentAction,
    PerformanceMetric,
    PerformanceOutcome,
    ProcurementPublicationEvent,
    ProcurementActionCase,
)


def public_procurement_schema_bundle() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "models": {model.__name__: model.model_json_schema() for model in PUBLIC_PROCUREMENT_MODELS},
    }
