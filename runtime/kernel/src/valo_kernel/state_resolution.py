from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .authority_projection import AuthorityStateReference
from .contracts import canonical_digest

ContinuityStatus = Literal["CONTINUOUS", "INVALIDATED", "UNKNOWN"]


class StateFactRequirement(BaseModel):
    schema_version: Literal["state_fact_requirement.v1"] = "state_fact_requirement.v1"
    requirement_id: str
    source_id: str
    fact_type: str
    authority_critical: bool = True
    require_causal_continuity: bool = True
    must_be_current_at_commit: bool = True
    max_staleness_seconds: int | None = Field(default=None, ge=0)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_requirement(self) -> StateFactRequirement:
        if not self.requirement_id or not self.source_id or not self.fact_type:
            raise ValueError("state fact requirement fields are required")
        if self.authority_critical and not self.require_causal_continuity:
            raise ValueError("authority-critical facts require causal continuity")
        return self


class SourceFactObservation(BaseModel):
    schema_version: Literal["source_fact_observation.v1"] = "source_fact_observation.v1"
    tenant_id: str
    source_id: str
    fact_id: str
    fact_type: str
    source_version: str
    value_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    provenance_ref: str
    effective_at: datetime
    observed_at: datetime
    valid_until: datetime | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_observation(self) -> SourceFactObservation:
        required = (
            self.tenant_id,
            self.source_id,
            self.fact_id,
            self.fact_type,
            self.source_version,
            self.provenance_ref,
        )
        if any(not item for item in required):
            raise ValueError("source fact observation fields are required")
        if self.effective_at > self.observed_at:
            raise ValueError("source fact cannot be observed before it is effective")
        if self.valid_until is not None and self.valid_until <= self.observed_at:
            raise ValueError("source fact validity must extend beyond observation")
        return self


class CausalContinuityProof(BaseModel):
    schema_version: Literal["causal_continuity_proof.v1"] = "causal_continuity_proof.v1"
    tenant_id: str
    source_id: str
    fact_id: str
    observed_version: str
    checked_version: str
    status: ContinuityStatus
    checked_at: datetime
    valid_until: datetime
    proof_ref: str
    invalidating_refs: tuple[str, ...] = ()
    proof_digest: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"proof_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_proof(self) -> CausalContinuityProof:
        required = (
            self.tenant_id,
            self.source_id,
            self.fact_id,
            self.observed_version,
            self.checked_version,
            self.proof_ref,
        )
        if any(not item for item in required):
            raise ValueError("causal continuity proof fields are required")
        if self.valid_until <= self.checked_at:
            raise ValueError("causal continuity proof must have a positive validity window")
        if self.status == "CONTINUOUS" and self.invalidating_refs:
            raise ValueError("continuous proof cannot carry invalidating interventions")
        if self.status == "INVALIDATED" and not self.invalidating_refs:
            raise ValueError("invalidated proof must identify an intervention")
        if self.proof_digest and self.proof_digest != self.computed_digest:
            raise ValueError("causal continuity proof digest mismatch")
        return self


class ResolvedStateFact(BaseModel):
    requirement: StateFactRequirement
    observation: SourceFactObservation
    continuity: CausalContinuityProof | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)


class GovernedStateBundle(BaseModel):
    schema_version: Literal["governed_state_bundle.v1"] = "governed_state_bundle.v1"
    tenant_id: str
    evaluated_at: datetime
    facts: tuple[ResolvedStateFact, ...]
    dependency_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    continuity_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    valid_until: datetime
    bundle_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"bundle_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_bundle(self) -> GovernedStateBundle:
        if not self.tenant_id:
            raise ValueError("state bundle tenant is required")
        if not self.facts:
            raise ValueError("state bundle requires at least one fact")
        requirement_ids = [item.requirement.requirement_id for item in self.facts]
        if len(set(requirement_ids)) != len(requirement_ids):
            raise ValueError("state bundle requirement ids must be unique")
        if self.valid_until <= self.evaluated_at:
            raise ValueError("state bundle must be valid after evaluation")
        if self.bundle_digest and self.bundle_digest != self.computed_digest:
            raise ValueError("state bundle digest mismatch")
        return self


def seal_causal_continuity_proof(
    *,
    tenant_id: str,
    source_id: str,
    fact_id: str,
    observed_version: str,
    checked_version: str,
    status: ContinuityStatus,
    checked_at: datetime,
    valid_until: datetime,
    proof_ref: str,
    invalidating_refs: tuple[str, ...] = (),
) -> CausalContinuityProof:
    unsealed = CausalContinuityProof(
        tenant_id=tenant_id,
        source_id=source_id,
        fact_id=fact_id,
        observed_version=observed_version,
        checked_version=checked_version,
        status=status,
        checked_at=checked_at,
        valid_until=valid_until,
        proof_ref=proof_ref,
        invalidating_refs=invalidating_refs,
    )
    return CausalContinuityProof.model_validate(
        {**unsealed.model_dump(mode="python"), "proof_digest": unsealed.computed_digest}
    )


def resolve_state_bundle(
    *,
    tenant_id: str,
    requirements: tuple[StateFactRequirement, ...],
    observations: tuple[SourceFactObservation, ...],
    continuity_proofs: tuple[CausalContinuityProof, ...],
    evaluated_at: datetime,
) -> GovernedStateBundle:
    if not tenant_id:
        raise ValueError("tenant id is required")
    if not requirements:
        raise ValueError("at least one state requirement is required")
    if len({item.requirement_id for item in requirements}) != len(requirements):
        raise ValueError("state requirement ids must be unique")

    observation_index: dict[tuple[str, str], list[SourceFactObservation]] = {}
    for observation in observations:
        observation_index.setdefault(
            (observation.source_id, observation.fact_type), []
        ).append(observation)

    proof_index: dict[tuple[str, str], list[CausalContinuityProof]] = {}
    for proof in continuity_proofs:
        proof_index.setdefault((proof.source_id, proof.fact_id), []).append(proof)

    resolved: list[ResolvedStateFact] = []
    validity_bounds: list[datetime] = []
    continuity_digests: list[str] = []

    for requirement in requirements:
        matches = observation_index.get((requirement.source_id, requirement.fact_type), [])
        if not matches:
            raise ValueError(
                f"required source fact is missing: {requirement.requirement_id}"
            )
        if len(matches) != 1:
            raise ValueError(
                f"required source fact is ambiguous: {requirement.requirement_id}"
            )
        observation = matches[0]
        if observation.tenant_id != tenant_id:
            raise ValueError("source fact tenant mismatch")
        if observation.observed_at > evaluated_at:
            raise ValueError("source fact observation is from the future")
        if observation.valid_until is not None:
            if evaluated_at >= observation.valid_until:
                raise ValueError(
                    f"source fact is no longer valid: {requirement.requirement_id}"
                )
            validity_bounds.append(observation.valid_until)
        if requirement.max_staleness_seconds is not None:
            freshness_limit = observation.observed_at + timedelta(
                seconds=requirement.max_staleness_seconds
            )
            if evaluated_at > freshness_limit:
                raise ValueError(
                    f"source fact exceeds bounded staleness: {requirement.requirement_id}"
                )
            validity_bounds.append(freshness_limit)

        continuity: CausalContinuityProof | None = None
        if requirement.require_causal_continuity:
            proofs = proof_index.get((observation.source_id, observation.fact_id), [])
            if not proofs:
                raise ValueError(
                    f"causal continuity proof is required: {requirement.requirement_id}"
                )
            if len(proofs) != 1:
                raise ValueError(
                    f"causal continuity proof is ambiguous: {requirement.requirement_id}"
                )
            continuity = proofs[0]
            if continuity.tenant_id != tenant_id:
                raise ValueError("causal continuity proof tenant mismatch")
            if continuity.observed_version != observation.source_version:
                raise ValueError(
                    f"causal continuity version mismatch: {requirement.requirement_id}"
                )
            if continuity.proof_digest != continuity.computed_digest:
                raise ValueError("causal continuity proof is unsealed or tampered")
            if continuity.status != "CONTINUOUS":
                raise ValueError(
                    f"causal continuity is not established: {requirement.requirement_id}"
                )
            if continuity.checked_at > evaluated_at:
                raise ValueError("causal continuity check is from the future")
            if requirement.must_be_current_at_commit and continuity.checked_at != evaluated_at:
                raise ValueError(
                    f"causal continuity was not checked at commit evaluation: {requirement.requirement_id}"
                )
            if evaluated_at >= continuity.valid_until:
                raise ValueError(
                    f"causal continuity proof expired: {requirement.requirement_id}"
                )
            validity_bounds.append(continuity.valid_until)
            continuity_digests.append(continuity.proof_digest)

        resolved.append(
            ResolvedStateFact(
                requirement=requirement,
                observation=observation,
                continuity=continuity,
            )
        )

    if not validity_bounds:
        raise ValueError("state bundle has no explicit validity bound")
    valid_until = min(validity_bounds)
    continuity_digest = canonical_digest(sorted(continuity_digests))
    source_dependencies = [
        {
            "requirement_id": item.requirement.requirement_id,
            "source_id": item.observation.source_id,
            "fact_id": item.observation.fact_id,
            "fact_type": item.observation.fact_type,
            "source_version": item.observation.source_version,
            "value_digest": item.observation.value_digest,
            "provenance_ref": item.observation.provenance_ref,
        }
        for item in resolved
    ]
    dependency_digest = canonical_digest(
        {
            "source_dependencies": source_dependencies,
            "continuity_digest": continuity_digest,
        }
    )
    unsealed = GovernedStateBundle(
        tenant_id=tenant_id,
        evaluated_at=evaluated_at,
        facts=tuple(resolved),
        dependency_digest=dependency_digest,
        continuity_digest=continuity_digest,
        valid_until=valid_until,
    )
    return GovernedStateBundle.model_validate(
        {**unsealed.model_dump(mode="python"), "bundle_digest": unsealed.computed_digest}
    )


def authority_state_reference_from_bundle(
    *,
    bundle: GovernedStateBundle,
    state_root: str,
) -> AuthorityStateReference:
    if bundle.bundle_digest != bundle.computed_digest:
        raise ValueError("state bundle is unsealed or tampered")
    observed_at = min(item.observation.observed_at for item in bundle.facts)
    return AuthorityStateReference(
        tenant_id=bundle.tenant_id,
        state_root=state_root,
        dependency_digest=bundle.dependency_digest,
        observed_at=observed_at,
        valid_until=bundle.valid_until,
    )
