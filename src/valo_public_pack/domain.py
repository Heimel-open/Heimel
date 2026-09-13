from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class CaseState(str, Enum):
    RECEIVED = "RECEIVED"
    REGISTERED = "REGISTERED"
    AWAITING_INFORMATION = "AWAITING_INFORMATION"
    READY_FOR_REVIEW = "READY_FOR_REVIEW"
    UNDER_REVIEW = "UNDER_REVIEW"
    READY_FOR_DECISION = "READY_FOR_DECISION"
    DECIDED = "DECIDED"
    NOTIFIED = "NOTIFIED"
    APPEAL_PERIOD = "APPEAL_PERIOD"
    APPEALED = "APPEALED"
    FINAL = "FINAL"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    EXCEPTION = "EXCEPTION"


class EligibilityOutcome(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    UNKNOWN = "UNKNOWN"
    REQUIRES_REVIEW = "REQUIRES_REVIEW"


class ConflictOfInterestOutcome(str, Enum):
    CLEAR = "CLEAR"
    POTENTIAL_CONFLICT = "POTENTIAL_CONFLICT"
    DISQUALIFIED = "DISQUALIFIED"
    UNKNOWN = "UNKNOWN"


class RightsEffect(str, Enum):
    RIGHT_GRANTED = "RIGHT_GRANTED"
    RIGHT_DENIED = "RIGHT_DENIED"
    RIGHT_CHANGED = "RIGHT_CHANGED"
    NO_RIGHT_EFFECT = "NO_RIGHT_EFFECT"


class ObligationEffect(str, Enum):
    OBLIGATION_CREATED = "OBLIGATION_CREATED"
    OBLIGATION_CHANGED = "OBLIGATION_CHANGED"
    OBLIGATION_SATISFIED = "OBLIGATION_SATISFIED"
    NO_OBLIGATION_EFFECT = "NO_OBLIGATION_EFFECT"


class NotificationState(str, Enum):
    SENT = "SENT"
    DELIVERED = "DELIVERED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    FAILED = "FAILED"


class CaseException(str, Enum):
    IDENTITY_UNVERIFIED = "IDENTITY_UNVERIFIED"
    REPRESENTATION_INVALID = "REPRESENTATION_INVALID"
    LEGAL_BASIS_MISSING = "LEGAL_BASIS_MISSING"
    LEGAL_BASIS_EXPIRED = "LEGAL_BASIS_EXPIRED"
    COMPETENCE_MISSING = "COMPETENCE_MISSING"
    COMPETENCE_REVOKED = "COMPETENCE_REVOKED"
    EVIDENCE_MISSING = "EVIDENCE_MISSING"
    EVIDENCE_CONFLICTED = "EVIDENCE_CONFLICTED"
    FACT_UNKNOWN = "FACT_UNKNOWN"
    PROCEDURAL_REQUIREMENT_MISSING = "PROCEDURAL_REQUIREMENT_MISSING"
    CONFLICT_OF_INTEREST = "CONFLICT_OF_INTEREST"
    DEADLINE_EXPIRED = "DEADLINE_EXPIRED"
    RIGHTS_EFFECT_UNRESOLVED = "RIGHTS_EFFECT_UNRESOLVED"
    NOTIFICATION_FAILED = "NOTIFICATION_FAILED"
    EXTERNAL_STATE_DIVERGED = "EXTERNAL_STATE_DIVERGED"
    PURPOSE_VIOLATION = "PURPOSE_VIOLATION"


@dataclass
class CaseExceptionRecord:
    code: CaseException
    case_id: str
    reason: str
    step: str | None = None


# Public domain type names (opaque FF types — only in this pack).
class PublicType:
    APPLICANT = "Applicant"
    REPRESENTATIVE = "Representative"
    PUBLIC_BODY = "PublicBody"
    ADMINISTRATIVE_UNIT = "AdministrativeUnit"
    CASE = "Case"
    APPLICATION = "Application"
    PUBLIC_SERVICE = "PublicService"
    LEGAL_BASIS = "LegalBasis"
    COMPETENCE = "Competence"
    DELEGATION = "Delegation"
    RIGHT = "Right"
    OBLIGATION = "Obligation"
    REQUIREMENT = "Requirement"
    EVIDENCE_REQUIREMENT = "EvidenceRequirement"
    EVIDENCE_SUBMISSION = "EvidenceSubmission"
    CASE_FACT = "CaseFact"
    ELIGIBILITY_ASSESSMENT = "EligibilityAssessment"
    DECISION_BASIS = "DecisionBasis"
    PUBLIC_DECISION = "PublicDecision"
    NOTIFICATION = "Notification"
    DEADLINE = "Deadline"
    APPEAL_RIGHT = "AppealRight"
    APPEAL = "Appeal"
    CASE_EXCEPTION = "CaseException"


def verified(base: str) -> str:
    return f"Verified<{base}>"


def admitted(base: str) -> str:
    return f"Admitted<{base}>"


def confirmed(base: str) -> str:
    return f"Confirmed<{base}>"


def multi(base: str, *refinements: str) -> str:
    return f"{base}{{{','.join(refinements)}}}"
