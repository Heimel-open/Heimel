from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class WorkOrderState(str, Enum):
    NEW = "NEW"
    QUALIFYING = "QUALIFYING"
    READY_TO_QUOTE = "READY_TO_QUOTE"
    QUOTED = "QUOTED"
    ACCEPTED = "ACCEPTED"
    READY_TO_SCHEDULE = "READY_TO_SCHEDULE"
    SCHEDULED = "SCHEDULED"
    DISPATCHED = "DISPATCHED"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_EVIDENCE = "AWAITING_EVIDENCE"
    COMPLETED = "COMPLETED"
    INVOICED = "INVOICED"
    PAID = "PAID"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    EXCEPTION = "EXCEPTION"


WORK_ORDER_FLOW = [state for state in WorkOrderState]


class TradeException(str, Enum):
    MISSING_CUSTOMER_INFORMATION = "MISSING_CUSTOMER_INFORMATION"
    NO_QUALIFIED_WORKER = "NO_QUALIFIED_WORKER"
    CREDENTIAL_EXPIRED = "CREDENTIAL_EXPIRED"
    NO_AVAILABLE_SLOT = "NO_AVAILABLE_SLOT"
    MATERIAL_UNAVAILABLE = "MATERIAL_UNAVAILABLE"
    QUOTE_REJECTED = "QUOTE_REJECTED"
    CUSTOMER_NO_RESPONSE = "CUSTOMER_NO_RESPONSE"
    WORK_EVIDENCE_MISSING = "WORK_EVIDENCE_MISSING"
    WORK_EVIDENCE_CONFLICT = "WORK_EVIDENCE_CONFLICT"
    INVOICE_MISMATCH = "INVOICE_MISMATCH"
    PAYMENT_MISSING = "PAYMENT_MISSING"
    EXTERNAL_EFFECT_DIVERGED = "EXTERNAL_EFFECT_DIVERGED"
    REVOKED_AUTHORITY = "REVOKED_AUTHORITY"


@dataclass
class TradeExceptionRecord:
    code: TradeException
    work_order_id: str
    reason: str
    step: str | None = None


# Domain type names used in Function Fabric type expressions. These are opaque
# FF types; none of them require changes to Kernel core.
class DomainType:
    CUSTOMER = "Customer"
    SERVICE_REQUEST = "ServiceRequest"
    SITE = "Site"
    SERVICE = "Service"
    WORK_ORDER = "WorkOrder"
    WORKER = "Worker"
    ELECTRICIAN = "Electrician"
    CREDENTIAL = "Credential"
    APPOINTMENT = "Appointment"
    ESTIMATE = "Estimate"
    QUOTE = "Quote"
    MATERIAL_REQUIREMENT = "MaterialRequirement"
    MATERIAL = "Material"
    CHECKLIST = "Checklist"
    FINDING = "Finding"
    COMPLETION_EVIDENCE = "CompletionEvidence"
    INVOICE = "Invoice"
    PAYMENT_OBLIGATION = "PaymentObligation"
    PAYMENT = "Payment"
    REQUEST = "Request"
    CLASSIFICATION = "Classification"
    SITE_ASSESSMENT = "SiteAssessment"


def verified(base: str) -> str:
    return f"Verified<{base}>"


def admitted(base: str) -> str:
    return f"Admitted<{base}>"


def confirmed(base: str) -> str:
    return f"Confirmed<{base}>"


def reserved(base: str) -> str:
    return f"Reserved<{base}>"


def multi(base: str, *refinements: str) -> str:
    return f"{base}{{{','.join(refinements)}}}"
