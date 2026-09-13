"""Versioned public-procurement state and evidence contracts.

These immutable records describe a procurement process. They do not evaluate
authority, execute payments, or replace REHT/institutional decision-makers.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Mapping


def _canonical_digest(payload: Mapping[str, object]) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


class _Digestible:
    def canonical_payload(self) -> Mapping[str, object]:
        return asdict(self)  # type: ignore[arg-type]

    @property
    def computed_digest(self) -> str:
        return _canonical_digest(self.canonical_payload())


@dataclass(frozen=True)
class ProcurementProcedure(_Digestible):
    procedure_id: str
    tenant_id: str
    procedure_type: str
    status: str
    needs_plan_ref: str | None = None
    estimated_value_nok: float | None = None
    currency: str = "NOK"
    award_type: str | None = None
    policy_version: str | None = None
    criteria_version: str | None = None
    opening_at: str | None = None
    closing_at: str | None = None
    data_space_target: str | None = None
    publication_event_digest: str | None = None
    schema_version: str = "v1"


@dataclass(frozen=True)
class NeedsPlan(_Digestible):
    needs_plan_id: str
    tenant_id: str
    fiscal_year: str
    purpose: str
    description: str
    budget_nok: float
    approval_ref: str | None = None
    schema_version: str = "v1"


@dataclass(frozen=True)
class EconomicOperator(_Digestible):
    operator_id: str
    name: str
    organization_number: str
    country_code: str
    risk_tier: str = "LOW"
    status: str = "ACTIVE"
    bank_account_ref: str | None = None
    ownership_country_code: str | None = None
    data_location_eea: bool = True
    eligibility_status: str = "ELIGIBLE"
    schema_version: str = "v1"


@dataclass(frozen=True)
class EligibilityEvidence(_Digestible):
    evidence_id: str
    operator_id: str
    evidence_type: str
    issuer: str
    issued_at: str
    evidence_digest: str
    expires_at: str | None = None
    validity_status: str = "VALID"
    schema_version: str = "v1"


@dataclass(frozen=True)
class Tender(_Digestible):
    tender_id: str
    procedure_id: str
    operator_id: str
    price_nok: float
    provenance_ref: str
    submitted_at: str
    technical_score: float | None = None
    quality_score: float | None = None
    tender_language: str = "no"
    schema_version: str = "v1"


@dataclass(frozen=True)
class EvaluationCriterion(_Digestible):
    criterion_id: str
    procedure_id: str
    name: str
    description: str
    weight: float
    evaluation_type: str = "QUALITY"
    criteria_version: str | None = None
    schema_version: str = "v1"


@dataclass(frozen=True)
class EvaluationResult(_Digestible):
    result_id: str
    tender_id: str
    criterion_id: str
    score: float
    evaluator: str
    confidence: float | None = None
    ambiguity_flag: bool = False
    notes: str = ""
    schema_version: str = "v1"


@dataclass(frozen=True)
class AwardRecommendation(_Digestible):
    recommendation_id: str
    procedure_id: str
    winning_tender_id: str
    rationale: str
    criteria_version: str
    evaluation_digest: str
    recommended_by: str
    created_at: str
    schema_version: str = "v1"


@dataclass(frozen=True)
class AwardDecision(_Digestible):
    """Institutional decision record; authority is referenced, not granted."""

    decision_id: str
    procedure_id: str
    tender_id: str
    decided_by: str
    authority_ref: str
    decided_at: str
    basis_ref: str | None = None
    reht_clearance_ref: str | None = None
    schema_version: str = "v1"


@dataclass(frozen=True)
class PublicContract(_Digestible):
    contract_id: str
    procedure_id: str
    operator_id: str
    value_nok: float
    term_start: str
    term_end: str | None = None
    currency: str = "NOK"
    status: str = "ACTIVE"
    signature_ref: str | None = None
    publication_ref: str | None = None
    schema_version: str = "v1"


@dataclass(frozen=True)
class ContractModification(_Digestible):
    modification_id: str
    contract_id: str
    change_type: str
    description: str
    value_delta_nok: float = 0.0
    approved_by: str | None = None
    approved_at: str | None = None
    reht_clearance_ref: str | None = None
    schema_version: str = "v1"


@dataclass(frozen=True)
class SupplierChange(_Digestible):
    change_id: str
    contract_id: str
    operator_id: str
    change_type: str
    old_value: str | None = None
    new_value: str | None = None
    cleared_at: str | None = None
    reht_clearance_ref: str | None = None
    schema_version: str = "v1"


@dataclass(frozen=True)
class Invoice(_Digestible):
    invoice_id: str
    contract_id: str
    operator_id: str
    invoice_number: str
    amount_nok: float
    issued_at: str
    currency: str = "NOK"
    status: str = "RECEIVED"
    payment_ref: str | None = None
    schema_version: str = "v1"


@dataclass(frozen=True)
class PaymentAction(_Digestible):
    """Payment proposal record; it does not perform or authorize payment."""

    payment_id: str
    invoice_id: str
    contract_id: str
    operator_id: str
    amount_nok: float
    requested_at: str
    currency: str = "NOK"
    status: str = "REQUESTED"
    executed_at: str | None = None
    reht_clearance_ref: str | None = None
    schema_version: str = "v1"


@dataclass(frozen=True)
class PerformanceOutcome(_Digestible):
    outcome_id: str
    contract_id: str
    period: str
    on_time_delivery_rate: float | None = None
    quality_score: float | None = None
    rating: str | None = None
    notes: str = ""
    schema_version: str = "v1"


@dataclass(frozen=True)
class ProcurementPublicationEvent(_Digestible):
    event_id: str
    procedure_id: str
    data_space_target: str
    event_type: str
    payload_digest: str
    published_at: str
    publication_ref: str | None = None
    schema_version: str = "v1"
