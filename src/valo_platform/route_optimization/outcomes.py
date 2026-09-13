"""Verified route outcomes and authority-neutral estimate update proposals."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.valo_platform.action_envelope.receipt_ledger import (
    LedgerEntry,
    SQLiteReceiptLedger,
    TrustedReceiptIssuer,
)
from src.valo_platform.canonical import canonical_digest
from src.valo_platform.route_optimization.contracts import RouteEstimate
from src.valo_platform.route_optimization.metrics import RouteWorkMeasurement
from src.valo_platform.route_optimization.receipts import (
    ROUTE_OUTCOME_ARTIFACT_TYPE,
    sign_route_artifact,
)


class ObservedEstimateComponents(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    execution_ms: int = Field(ge=0)
    queue_ms: int = Field(default=0, ge=0)
    human_wait_ms: int = Field(default=0, ge=0)
    retry_ms: int = Field(default=0, ge=0)
    rollback_ms: int = Field(default=0, ge=0)
    cost_microunits: int = Field(ge=0)

    @property
    def digest(self) -> str:
        return canonical_digest(self)


class VerifiedRouteOutcome(BaseModel):
    """Evidence-backed observation of what happened after governed execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "verified_route_outcome.v1"
    outcome_id: str
    tenant_id: str
    execution_id: str
    route_request_id: str
    route_digest: str
    route_commit_binding_digest: str
    intended_outcome_ref: str
    success: bool
    observed_at: datetime
    work_measurement: RouteWorkMeasurement
    estimate_components: ObservedEstimateComponents
    evidence_refs: tuple[str, ...]
    verifier_id: str
    verification_method: str
    previous_receipt_hash: str
    outcome_digest: str

    @field_validator("evidence_refs", mode="before")
    @classmethod
    def _require_evidence(cls, value: object) -> object:
        values = tuple(sorted(set(value or ())))
        if not values:
            raise ValueError("verified outcome requires evidence references")
        return values

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.model_copy(update={"outcome_digest": ""}))


class EstimateUpdateProposal(BaseModel):
    """Proposal only; cannot change authority, policy, validity or clearance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "route_estimate_update_proposal.v1"
    proposal_id: str
    outcome_digest: str
    previous_estimate_digest: str
    previous_estimate: RouteEstimate
    proposed_estimate: RouteEstimate
    learning_rate_bps: int = Field(ge=1, le=10000)
    updated_fields: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    authority_effect: Literal["none"] = "none"
    policy_effect: Literal["none"] = "none"
    route_validity_effect: Literal["none"] = "none"
    clearance_effect: Literal["none"] = "none"
    proposal_digest: str

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.model_copy(update={"proposal_digest": ""}))


def seal_verified_route_outcome(
    *,
    outcome_id: str,
    tenant_id: str,
    execution_id: str,
    route_request_id: str,
    route_digest: str,
    route_commit_binding_digest: str,
    intended_outcome_ref: str,
    success: bool,
    observed_at: datetime,
    work_measurement: RouteWorkMeasurement,
    estimate_components: ObservedEstimateComponents,
    evidence_refs: tuple[str, ...],
    verifier_id: str,
    verification_method: str,
    previous_receipt_hash: str,
) -> VerifiedRouteOutcome:
    required = (
        outcome_id,
        tenant_id,
        execution_id,
        route_request_id,
        route_digest,
        route_commit_binding_digest,
        intended_outcome_ref,
        verifier_id,
        verification_method,
        previous_receipt_hash,
    )
    if not all(required):
        raise ValueError("verified outcome identities and bindings are required")
    provisional = VerifiedRouteOutcome(
        outcome_id=outcome_id,
        tenant_id=tenant_id,
        execution_id=execution_id,
        route_request_id=route_request_id,
        route_digest=route_digest,
        route_commit_binding_digest=route_commit_binding_digest,
        intended_outcome_ref=intended_outcome_ref,
        success=success,
        observed_at=observed_at,
        work_measurement=work_measurement,
        estimate_components=estimate_components,
        evidence_refs=evidence_refs,
        verifier_id=verifier_id,
        verification_method=verification_method,
        previous_receipt_hash=previous_receipt_hash,
        outcome_digest="",
    )
    return provisional.model_copy(
        update={"outcome_digest": provisional.computed_digest}
    )


def append_verified_route_outcome(
    *,
    ledger: SQLiteReceiptLedger,
    outcome: VerifiedRouteOutcome,
    private_key: Ed25519PrivateKey,
    trusted_issuer: TrustedReceiptIssuer,
    expires_at: datetime,
    recorded_at: datetime | None = None,
) -> LedgerEntry:
    if outcome.tenant_id != trusted_issuer.tenant_id:
        raise ValueError("outcome tenant differs from trusted issuer")
    if outcome.computed_digest != outcome.outcome_digest:
        raise ValueError("verified outcome digest mismatch")
    artifact = sign_route_artifact(
        payload=outcome,
        artifact_id=outcome.outcome_id,
        artifact_type=ROUTE_OUTCOME_ARTIFACT_TYPE,
        private_key=private_key,
        issuer=trusted_issuer,
        issued_at=outcome.observed_at,
        expires_at=expires_at,
    )
    return ledger.append(
        execution_id=outcome.execution_id,
        artifact=artifact,
        trusted_issuer=trusted_issuer,
        recorded_at=recorded_at,
    )


def _blend(previous: int, observed: int, learning_rate_bps: int) -> int:
    retained = previous * (10000 - learning_rate_bps)
    learned = observed * learning_rate_bps
    return (retained + learned + 5000) // 10000


def propose_estimate_update(
    *,
    proposal_id: str,
    previous: RouteEstimate,
    outcome: VerifiedRouteOutcome,
    learning_rate_bps: int = 2000,
) -> EstimateUpdateProposal:
    """Create a deterministic performance-only update proposal."""
    if outcome.computed_digest != outcome.outcome_digest:
        raise ValueError("verified outcome digest mismatch")
    if not 1 <= learning_rate_bps <= 10000:
        raise ValueError("learning rate must be between 1 and 10000 bps")
    observed = outcome.estimate_components
    proposed = RouteEstimate(
        execution_ms=_blend(
            previous.execution_ms,
            observed.execution_ms,
            learning_rate_bps,
        ),
        queue_ms=_blend(
            previous.queue_ms,
            observed.queue_ms,
            learning_rate_bps,
        ),
        human_wait_ms=_blend(
            previous.human_wait_ms,
            observed.human_wait_ms,
            learning_rate_bps,
        ),
        expected_retry_ms=_blend(
            previous.expected_retry_ms,
            observed.retry_ms,
            learning_rate_bps,
        ),
        expected_rollback_ms=_blend(
            previous.expected_rollback_ms,
            observed.rollback_ms,
            learning_rate_bps,
        ),
        cost_microunits=_blend(
            previous.cost_microunits,
            observed.cost_microunits,
            learning_rate_bps,
        ),
        risk_exposure=previous.risk_exposure,
        reversibility=previous.reversibility,
        evidence_strength=previous.evidence_strength,
        confidence=previous.confidence,
        source_ref=f"verified-outcome:{outcome.outcome_digest}",
        version=(
            f"{previous.version}+outcome."
            f"{outcome.outcome_digest.removeprefix('sha256:')[:12]}"
        ),
    )
    provisional = EstimateUpdateProposal(
        proposal_id=proposal_id,
        outcome_digest=outcome.outcome_digest,
        previous_estimate_digest=canonical_digest(previous),
        previous_estimate=previous,
        proposed_estimate=proposed,
        learning_rate_bps=learning_rate_bps,
        updated_fields=(
            "execution_ms",
            "queue_ms",
            "human_wait_ms",
            "expected_retry_ms",
            "expected_rollback_ms",
            "cost_microunits",
        ),
        evidence_refs=outcome.evidence_refs,
        proposal_digest="",
    )
    return provisional.model_copy(
        update={"proposal_digest": provisional.computed_digest}
    )


__all__ = [
    "EstimateUpdateProposal",
    "ObservedEstimateComponents",
    "VerifiedRouteOutcome",
    "append_verified_route_outcome",
    "propose_estimate_update",
    "seal_verified_route_outcome",
]
