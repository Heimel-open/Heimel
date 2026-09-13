from __future__ import annotations

from datetime import datetime
from fnmatch import fnmatchcase

from ..contracts.common import canonical_digest
from ..contracts.drp import (
    DrpActionDescriptor,
    DrpDelegationReceipt,
    DrpInteropAssessment,
    DrpVerificationEvidence,
)


def _pattern_covers(parent: str, child: str) -> bool:
    if parent == "*" or parent == child:
        return True
    if "*" not in child:
        return fnmatchcase(child, parent)
    if parent.endswith("*") and child.endswith("*"):
        return child[:-1].startswith(parent[:-1])
    return False


def _action_covers(parent: DrpActionDescriptor, child: DrpActionDescriptor) -> bool:
    return _pattern_covers(parent.operation, child.operation) and _pattern_covers(
        parent.resource, child.resource
    )


def _scope_subset(
    child: tuple[DrpActionDescriptor, ...],
    parent: tuple[DrpActionDescriptor, ...],
) -> bool:
    return all(any(_action_covers(p, c) for p in parent) for c in child)


def _strict_scope_attenuation(
    child: tuple[DrpActionDescriptor, ...],
    parent: tuple[DrpActionDescriptor, ...],
) -> bool:
    return _scope_subset(child, parent) and not _scope_subset(parent, child)


def _parent_denials_survive(
    child: tuple[DrpActionDescriptor, ...],
    parent: tuple[DrpActionDescriptor, ...],
) -> bool:
    return all(any(_action_covers(c, p) for c in child) for p in parent)


def _boundary_denies(boundary: str, action: DrpActionDescriptor) -> bool:
    parts = boundary.split(":", 2)
    if len(parts) != 3 or parts[0] != "deny":
        raise ValueError("unsupported DRP boundary format")
    operation, resource = parts[1], parts[2]
    return _pattern_covers(operation, action.operation) and _pattern_covers(
        resource, action.resource
    )


def _verification_reasons(
    receipt: DrpDelegationReceipt,
    verification: DrpVerificationEvidence,
    *,
    prefix: str = "",
) -> list[str]:
    reasons: list[str] = []
    tag = f"{prefix}_" if prefix else ""
    if verification.receipt_id != receipt.receipt_id:
        reasons.append(f"{tag}RECEIPT_ID_MISMATCH")
    if not verification.signature_verified:
        reasons.append(f"{tag}INVALID_SIGNATURE")
    if not verification.canonical_payload_verified:
        reasons.append(f"{tag}CANONICAL_PAYLOAD_UNVERIFIED")
    if not verification.log_anchor_verified:
        reasons.append(f"{tag}LOG_ANCHOR_UNVERIFIED")
    if not verification.revocation_checked:
        reasons.append(f"{tag}REVOCATION_UNCHECKED")
    if verification.revoked:
        reasons.append(f"{tag}RECEIPT_REVOKED")
    return reasons


def assess_drp_receipt(
    *,
    receipt: DrpDelegationReceipt,
    verification: DrpVerificationEvidence,
    action: DrpActionDescriptor,
    evaluated_at: datetime,
    current_authority_state_commitment: str | None,
    parent_receipt: DrpDelegationReceipt | None = None,
    parent_verification: DrpVerificationEvidence | None = None,
    ancestor_verifications: tuple[DrpVerificationEvidence, ...] = (),
) -> DrpInteropAssessment:
    reasons = _verification_reasons(receipt, verification)
    authority_state_match: bool | None = None

    if not (receipt.time_window.not_before <= evaluated_at < receipt.time_window.not_after):
        reasons.append("RECEIPT_OUTSIDE_TIME_WINDOW")

    matching_allows = [
        allowed for allowed in receipt.scope.allowed_actions if _action_covers(allowed, action)
    ]
    if not matching_allows:
        reasons.append("ACTION_NOT_IN_SCOPE")
    elif any(item.constraints and item.constraints != action.constraints for item in matching_allows):
        reasons.append("ACTION_CONSTRAINTS_UNVERIFIED")

    if any(_action_covers(denied, action) for denied in receipt.scope.denied_actions):
        reasons.append("ACTION_EXPLICITLY_DENIED")

    try:
        if any(_boundary_denies(boundary, action) for boundary in receipt.boundaries):
            reasons.append("ACTION_BOUNDARY_DENIED")
    except ValueError:
        reasons.append("UNSUPPORTED_BOUNDARY")

    if receipt.authority_state_commitment is not None:
        if current_authority_state_commitment is None:
            authority_state_match = False
            reasons.append("AUTHORITY_STATE_UNVERIFIED")
        else:
            authority_state_match = (
                receipt.authority_state_commitment
                == current_authority_state_commitment
            )
            if not authority_state_match:
                reasons.append("AUTHORITY_STATE_DRIFT")

    if receipt.parent_receipt_id is not None:
        if parent_receipt is None or parent_verification is None:
            reasons.append("PARENT_EVIDENCE_REQUIRED")
        else:
            reasons.extend(
                _verification_reasons(
                    parent_receipt,
                    parent_verification,
                    prefix="PARENT",
                )
            )
            if receipt.parent_receipt_id != parent_receipt.receipt_id:
                reasons.append("PARENT_RECEIPT_MISMATCH")
            if verification.orchestrator_binding_verified is not True:
                reasons.append("ORCHESTRATOR_BINDING_UNVERIFIED")
            child_window = receipt.time_window
            parent_window = parent_receipt.time_window
            if (
                child_window.not_before < parent_window.not_before
                or child_window.not_after > parent_window.not_after
            ):
                reasons.append("PARENT_TIME_WINDOW_VIOLATION")
            if not _strict_scope_attenuation(
                receipt.scope.allowed_actions,
                parent_receipt.scope.allowed_actions,
            ):
                reasons.append("SCOPE_NOT_STRICT_SUBSET")
            if not _parent_denials_survive(
                receipt.scope.denied_actions,
                parent_receipt.scope.denied_actions,
            ):
                reasons.append("PARENT_DENIAL_DROPPED")
            if not set(parent_receipt.boundaries).issubset(receipt.boundaries):
                reasons.append("PARENT_BOUNDARY_DROPPED")
    elif parent_receipt is not None or parent_verification is not None:
        reasons.append("UNEXPECTED_PARENT_EVIDENCE")

    for ancestor in ancestor_verifications:
        if not ancestor.signature_verified or not ancestor.canonical_payload_verified:
            reasons.append("ANCESTOR_CRYPTOGRAPHIC_EVIDENCE_INVALID")
        if not ancestor.log_anchor_verified:
            reasons.append("ANCESTOR_LOG_ANCHOR_UNVERIFIED")
        if not ancestor.revocation_checked:
            reasons.append("ANCESTOR_REVOCATION_UNCHECKED")
        if ancestor.revoked:
            reasons.append("ANCESTOR_REVOKED")

    reasons = list(dict.fromkeys(reasons))
    evidence_digest = canonical_digest(
        {
            "receipt": receipt.model_dump(mode="json", by_alias=True),
            "verification": verification.model_dump(mode="json"),
            "action": action.model_dump(mode="json"),
            "evaluated_at": evaluated_at.isoformat(),
            "current_authority_state_commitment": current_authority_state_commitment,
            "parent_receipt": (
                parent_receipt.model_dump(mode="json", by_alias=True)
                if parent_receipt is not None
                else None
            ),
            "parent_verification": (
                parent_verification.model_dump(mode="json")
                if parent_verification is not None
                else None
            ),
            "ancestor_verifications": [
                item.model_dump(mode="json") for item in ancestor_verifications
            ],
        }
    )
    return DrpInteropAssessment(
        receipt_id=receipt.receipt_id,
        admissible_as_evidence=not reasons,
        reasons=tuple(reasons),
        authority_state_match=authority_state_match,
        evidence_digest=evidence_digest,
    )
