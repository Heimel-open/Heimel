from __future__ import annotations

from typing import Any

from .domain import ConflictOfInterestOutcome


class PurposeViolation(Exception):
    """Evidence/data collected for one case type is reused for an unrelated
    action without a permitted purpose."""


def check_conflict_of_interest(decision_maker: str, applicant: str, relationships: list[dict[str, Any]]) -> ConflictOfInterestOutcome:
    """Input: decision maker, applicant, relationships, case. DISQUALIFIED
    blocks decision execution; POTENTIAL_CONFLICT requires review; UNKNOWN when
    the relationship picture is incomplete."""
    for relationship in relationships:
        if relationship.get("subject") == decision_maker and relationship.get("object") == applicant:
            kind = relationship.get("kind", "UNKNOWN")
            if kind in ("SPOUSE", "CHILD", "PARENT", "SIBLING", "SELF", "CLOSE_BUSINESS"):
                return ConflictOfInterestOutcome.DISQUALIFIED
            if kind == "POTENTIAL":
                return ConflictOfInterestOutcome.POTENTIAL_CONFLICT
            return ConflictOfInterestOutcome.UNKNOWN
    return ConflictOfInterestOutcome.CLEAR


def purpose_allows(evidence_purpose: str, case_purpose: str, permitted: list[str]) -> bool:
    """Purpose binding: data/evidence collected for one case type may only be
    used for a permitted action. Reuse for an unrelated purpose is denied."""
    if evidence_purpose == case_purpose:
        return True
    return evidence_purpose in permitted


def comparable_case_signature(facts: dict[str, Any], legal_basis: str, outcome: str) -> dict[str, Any]:
    """First cross-case control: similar facts + similar legal basis with a
    different outcome -> CONSISTENCY_REVIEW_REQUIRED. Never an automatic
    declaration of unlawful unequal treatment."""
    signature = {
        "facts": {k: v.get("object") for k, v in facts.items() if v.get("status") == "CONFIRMED"},
        "legal_basis": legal_basis,
        "outcome": outcome,
    }
    return signature


def equal_treatment_signal(signature_a: dict[str, Any], signature_b: dict[str, Any]) -> str:
    if (
        signature_a["facts"] == signature_b["facts"]
        and signature_a["legal_basis"] == signature_b["legal_basis"]
        and signature_a["outcome"] != signature_b["outcome"]
    ):
        return "CONSISTENCY_REVIEW_REQUIRED"
    return "NO_SIGNAL"
