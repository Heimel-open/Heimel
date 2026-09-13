"""Bind canonical SOL, MAL and VAIG inputs into route validity.

The adapter is constraint-only. It deliberately ignores positive decision
vocabulary as authority: governance inputs may invalidate or constrain a route,
but cannot issue clearance or authorize execution.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field

from src.valo_platform.action_envelope.mal_registry import (
    InvocationBinding,
    SignedApprovalRecord,
)
from src.valo_platform.api.schemas_governance import GovernanceEvaluationResponse
from src.valo_platform.canonical import canonical_digest
from src.valo_platform.route_optimization.contracts import (
    ConstraintKind,
    RouteCandidate,
    RouteConstraint,
    RouteRequest,
)
from src.valo_platform.sol.context import (
    ContextStatus,
    SOLContextEnvelope,
    Sensitivity,
)


def _same_hash(left: str, right: str) -> bool:
    return left.removeprefix("sha256:") == right.removeprefix("sha256:")


def _minimum_time(*values: Optional[datetime]) -> Optional[datetime]:
    present = [value for value in values if value is not None]
    return min(present) if present else None


class GovernanceInputSnapshot(BaseModel):
    """Versioned constraint bundle bound to one exact route request state."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    route_request_fingerprint: str
    sol_context_hash: str
    mal_approval_record_id: str
    mal_invocation_binding_hash: str
    vaig_receipt_id: str
    constraints: Tuple[RouteConstraint, ...]
    valid_until: Optional[datetime] = None
    risk_exposure: int = Field(default=0, ge=0, le=100)
    evidence_strength: int = Field(default=0, ge=0, le=100)

    @property
    def fingerprint(self) -> str:
        return canonical_digest(self)


class GovernanceInputPolicy(BaseModel):
    """Explicit route-input requirements; no implicit positive authority."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    require_purpose_match: bool = True
    require_permission_for_non_public: bool = True
    require_consent_for_confidential: bool = True
    minimum_vaig_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


def build_governance_input_snapshot(
    *,
    request: RouteRequest,
    sol_context: SOLContextEnvelope,
    mal_approval: SignedApprovalRecord,
    mal_binding: InvocationBinding,
    mal_secret: bytes,
    vaig_evaluation: GovernanceEvaluationResponse,
    policy: GovernanceInputPolicy = GovernanceInputPolicy(),
    expected_invocation_id: Optional[str] = None,
    vaig_valid_until: Optional[datetime] = None,
) -> GovernanceInputSnapshot:
    """Translate canonical governance artifacts into fail-closed constraints."""
    now = request.as_of
    sol_hash_matches = _same_hash(
        request.context_snapshot_hash,
        sol_context.envelope_hash,
    )
    sol_usable = sol_context.is_usable(now)
    purpose_matches = (
        sol_context.purpose == request.purpose_ref
        if policy.require_purpose_match
        else True
    )

    non_public_items = tuple(
        item
        for item in sol_context.items
        if item.sensitivity is not Sensitivity.PUBLIC
    )
    permission_valid = (
        bool(sol_context.permission_refs) or not non_public_items
        if policy.require_permission_for_non_public
        else True
    )
    confidential_items = tuple(
        item
        for item in sol_context.items
        if item.sensitivity in {Sensitivity.CONFIDENTIAL, Sensitivity.RESTRICTED}
    )
    consent_valid = (
        all(item.consent_ref for item in confidential_items)
        if policy.require_consent_for_confidential
        else True
    )

    mal_approval_valid = mal_approval.verify(mal_secret, now=now)
    mal_binding_active = mal_binding.expires_at > now
    mal_context_matches = _same_hash(
        mal_binding.sol_context_hash,
        sol_context.envelope_hash,
    )
    mal_approval_matches = _same_hash(
        mal_binding.approval_hash,
        mal_approval.approval_payload_hash,
    )
    mal_invocation_matches = (
        mal_binding.invocation_id == expected_invocation_id
        if expected_invocation_id is not None
        else True
    )
    mal_valid = all(
        (
            mal_approval_valid,
            mal_binding_active,
            mal_context_matches,
            mal_approval_matches,
            mal_invocation_matches,
        )
    )

    metadata = vaig_evaluation.metadata
    vaig_policy_conformant = metadata.get("policy_conformant") is True
    semantic_integrity = metadata.get("semantic_integrity_preserved") is True
    vaig_drift_free = not vaig_evaluation.drift_detected
    vaig_evidence_valid = (
        bool(vaig_evaluation.receipt_id)
        and vaig_evaluation.evidence_count > 0
        and vaig_evaluation.confidence >= policy.minimum_vaig_confidence
    )
    raw_risk = metadata.get("risk_exposure", 100)
    risk_exposure = (
        int(raw_risk)
        if isinstance(raw_risk, (int, float)) and 0 <= raw_risk <= 100
        else 100
    )
    risk_valid = (
        request.max_risk_exposure is None
        or risk_exposure <= request.max_risk_exposure
    )
    evidence_strength = max(
        0,
        min(100, round(vaig_evaluation.confidence * 100)),
    )

    sol_evidence = (f"sol:{sol_context.envelope_hash}",)
    mal_evidence = (
        f"mal-approval:{mal_approval.record_id}",
        f"mal-binding:{mal_binding.binding_hash}",
    )
    vaig_evidence = (f"vaig:{vaig_evaluation.receipt_id}",)

    constraints = (
        RouteConstraint(
            constraint_id="sol:active-context",
            kind=ConstraintKind.EVIDENCE,
            satisfied=sol_usable and sol_hash_matches,
            evidence_refs=sol_evidence,
            detail="SOL context must be active, unexpired and request-bound",
        ),
        RouteConstraint(
            constraint_id="sol:purpose-integrity",
            kind=ConstraintKind.SEMANTIC_INTEGRITY,
            satisfied=purpose_matches,
            evidence_refs=sol_evidence,
            detail="SOL purpose must match the route purpose",
        ),
        RouteConstraint(
            constraint_id="sol:permission-boundary",
            kind=ConstraintKind.PRIVACY,
            satisfied=permission_valid,
            evidence_refs=tuple(sol_context.permission_refs),
            detail="non-public SOL context requires permission binding",
        ),
        RouteConstraint(
            constraint_id="sol:consent-boundary",
            kind=ConstraintKind.CONSENT,
            satisfied=consent_valid,
            evidence_refs=tuple(
                sorted(
                    item.consent_ref
                    for item in confidential_items
                    if item.consent_ref
                )
            ),
            detail="confidential SOL context requires consent binding",
        ),
        RouteConstraint(
            constraint_id="mal:invocation-admissibility",
            kind=ConstraintKind.MAL_ADMISSIBILITY,
            satisfied=mal_valid,
            evidence_refs=mal_evidence,
            detail="MAL approval and invocation binding must match current runtime state",
        ),
        RouteConstraint(
            constraint_id="vaig:policy-conformance",
            kind=ConstraintKind.POLICY,
            satisfied=vaig_policy_conformant and vaig_drift_free,
            evidence_refs=vaig_evidence,
            detail="VAIG policy conformance must be explicit and drift-free",
        ),
        RouteConstraint(
            constraint_id="vaig:semantic-integrity",
            kind=ConstraintKind.SEMANTIC_INTEGRITY,
            satisfied=semantic_integrity,
            evidence_refs=vaig_evidence,
            detail="VAIG must explicitly preserve semantic integrity",
        ),
        RouteConstraint(
            constraint_id="vaig:evidence",
            kind=ConstraintKind.EVIDENCE,
            satisfied=vaig_evidence_valid,
            evidence_refs=vaig_evidence,
            detail="VAIG result requires a receipt, evidence and sufficient confidence",
        ),
        RouteConstraint(
            constraint_id="vaig:risk",
            kind=ConstraintKind.RISK,
            satisfied=risk_valid,
            evidence_refs=vaig_evidence,
            detail="VAIG risk exposure must remain within the route limit",
        ),
    )

    sol_item_valid_until = _minimum_time(
        *(item.valid_until for item in sol_context.items)
    )
    valid_until = _minimum_time(
        sol_context.expires_at,
        sol_item_valid_until,
        mal_approval.expires_at,
        mal_binding.expires_at,
        vaig_valid_until,
    )
    return GovernanceInputSnapshot(
        route_request_fingerprint=request.fingerprint,
        sol_context_hash=sol_context.envelope_hash,
        mal_approval_record_id=mal_approval.record_id,
        mal_invocation_binding_hash=mal_binding.binding_hash,
        vaig_receipt_id=vaig_evaluation.receipt_id,
        constraints=tuple(
            sorted(constraints, key=lambda constraint: constraint.constraint_id)
        ),
        valid_until=valid_until,
        risk_exposure=risk_exposure,
        evidence_strength=evidence_strength,
    )


def apply_governance_inputs(
    candidate: RouteCandidate,
    snapshot: GovernanceInputSnapshot,
    *,
    request: RouteRequest,
) -> RouteCandidate:
    """Bind the input snapshot into a candidate so route digests change on drift."""
    request_matches = snapshot.route_request_fingerprint == request.fingerprint
    request_binding = RouteConstraint(
        constraint_id="route:governance-input-request-binding",
        kind=ConstraintKind.EVIDENCE,
        satisfied=request_matches,
        evidence_refs=(f"governance-input:{snapshot.fingerprint}",),
        detail="governance inputs must bind to the exact current route request",
    )
    merged_by_id = {
        constraint.constraint_id: constraint
        for constraint in candidate.constraints
    }
    for constraint in snapshot.constraints + (request_binding,):
        merged_by_id[constraint.constraint_id] = constraint

    valid_until = _minimum_time(candidate.valid_until, snapshot.valid_until)
    return candidate.model_copy(
        update={
            "constraints": tuple(
                merged_by_id[key] for key in sorted(merged_by_id)
            ),
            "valid_until": valid_until,
            "assumptions": tuple(
                sorted(
                    set(candidate.assumptions)
                    | {f"governance-input:{snapshot.fingerprint}"}
                )
            ),
        }
    )


def governance_inputs_changed(
    previous_fingerprint: str,
    current: GovernanceInputSnapshot,
) -> bool:
    """Return True when SOL, MAL or VAIG state requires route re-planning."""
    return previous_fingerprint != current.fingerprint


__all__ = [
    "GovernanceInputPolicy",
    "GovernanceInputSnapshot",
    "apply_governance_inputs",
    "build_governance_input_snapshot",
    "governance_inputs_changed",
]
