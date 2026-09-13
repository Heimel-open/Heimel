from __future__ import annotations

from datetime import datetime, timedelta
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .authority_projection import PrincipalAuthoritySemantics
from .contracts import canonical_digest


class AttestationStage(StrEnum):
    PRE_COMMIT = "PRE_COMMIT"
    POST_EFFECT = "POST_EFFECT"


class AssuranceEvidenceKind(StrEnum):
    REHT_AUTHORIZATION = "REHT_AUTHORIZATION"
    RACS_DECISION = "RACS_DECISION"
    EFFECT_PATH_CONFORMANCE = "EFFECT_PATH_CONFORMANCE"
    EFFECT_RECEIPT = "EFFECT_RECEIPT"
    OUTCOME_EVIDENCE = "OUTCOME_EVIDENCE"


class AttestationDisposition(StrEnum):
    ATTESTED = "ATTESTED"
    NOT_ATTESTED = "NOT_ATTESTED"


class AssuranceEvidenceReference(BaseModel):
    """Opaque, digest-bound reference to assurance-relevant execution evidence.

    The referenced payload remains with the owning system or evidence store.
    This contract only binds the exact action/execution/authority semantics to
    the evidence digest that the insurer-facing assessment consumes.
    """

    schema_version: Literal["assurance_evidence_ref.v1"] = "assurance_evidence_ref.v1"
    evidence_id: str
    kind: AssuranceEvidenceKind
    action_id: str
    execution_ref: str
    authority_semantics_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_ref: str
    evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    observed_at: datetime
    valid_until: datetime
    decision_outcome: str | None = None
    effect_ref: str | None = None
    assertions: tuple[str, ...] = ()
    contradictory: bool = False
    reference_digest: str = ""

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"reference_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_reference(self) -> AssuranceEvidenceReference:
        required = (
            self.evidence_id,
            self.action_id,
            self.execution_ref,
            self.source_ref,
        )
        if any(not item for item in required):
            raise ValueError("assurance evidence identity fields are required")
        if self.valid_until <= self.observed_at:
            raise ValueError("assurance evidence must expire after observation")
        if self.kind is AssuranceEvidenceKind.RACS_DECISION and not self.decision_outcome:
            raise ValueError("RACS decision evidence requires decision_outcome")
        if self.kind is AssuranceEvidenceKind.EFFECT_PATH_CONFORMANCE and not self.assertions:
            raise ValueError("effect-path evidence requires control assertions")
        if self.kind in {
            AssuranceEvidenceKind.EFFECT_RECEIPT,
            AssuranceEvidenceKind.OUTCOME_EVIDENCE,
        } and not self.effect_ref:
            raise ValueError("effect and outcome evidence require effect_ref")
        if len(set(self.assertions)) != len(self.assertions):
            raise ValueError("assurance evidence assertions must be unique")
        if self.reference_digest and self.reference_digest != self.computed_digest:
            raise ValueError("assurance evidence reference digest mismatch")
        return self


class AgentRiskControlProfile(BaseModel):
    """Insurer-authored technical control condition, not an insurance decision."""

    schema_version: Literal["agent_risk_control_profile.v1"] = (
        "agent_risk_control_profile.v1"
    )
    profile_id: str
    insurer_ref: str
    product_ref: str
    effective_from: datetime
    valid_until: datetime
    required_pre_commit_evidence: tuple[AssuranceEvidenceKind, ...] = (
        AssuranceEvidenceKind.REHT_AUTHORIZATION,
        AssuranceEvidenceKind.RACS_DECISION,
        AssuranceEvidenceKind.EFFECT_PATH_CONFORMANCE,
    )
    required_post_effect_evidence: tuple[AssuranceEvidenceKind, ...] = (
        AssuranceEvidenceKind.REHT_AUTHORIZATION,
        AssuranceEvidenceKind.RACS_DECISION,
        AssuranceEvidenceKind.EFFECT_PATH_CONFORMANCE,
        AssuranceEvidenceKind.EFFECT_RECEIPT,
        AssuranceEvidenceKind.OUTCOME_EVIDENCE,
    )
    required_path_assertions: tuple[str, ...] = (
        "NO_DIRECT_EFFECT_PATH",
        "FRESH_AUTHORITY_AT_COMMIT",
        "GOVERNED_EFFECT_PATH",
        "NULL_EFFECT_ON_DENY",
    )
    accepted_racs_outcomes: tuple[str, ...] = ("ALLOW", "MODIFY")
    max_evidence_age_seconds: int = Field(default=900, gt=0)
    profile_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_determine_coverage: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"profile_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_profile(self) -> AgentRiskControlProfile:
        if not self.profile_id or not self.insurer_ref or not self.product_ref:
            raise ValueError("agent risk profile identity fields are required")
        if self.valid_until <= self.effective_from:
            raise ValueError("agent risk profile must have a positive validity window")
        for required in (
            self.required_pre_commit_evidence,
            self.required_post_effect_evidence,
        ):
            if not required or len(set(required)) != len(required):
                raise ValueError("required assurance evidence must be non-empty and unique")
        if not set(self.required_pre_commit_evidence).issubset(
            self.required_post_effect_evidence
        ):
            raise ValueError("post-effect evidence must include all pre-commit evidence")
        if len(set(self.required_path_assertions)) != len(self.required_path_assertions):
            raise ValueError("required path assertions must be unique")
        if not self.accepted_racs_outcomes:
            raise ValueError("at least one accepted RACS outcome is required")
        if self.profile_digest and self.profile_digest != self.computed_digest:
            raise ValueError("agent risk profile digest mismatch")
        return self


class AgentRiskAttestation(BaseModel):
    """Deterministic evidence-conformance result for an insurer integration.

    ATTESTED means the supplied evidence satisfies the technical profile. It
    does not mean an action is authorized, insured, covered or payable.
    """

    schema_version: Literal["agent_risk_attestation.v1"] = "agent_risk_attestation.v1"
    attestation_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    profile_id: str
    profile_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    insurer_ref: str
    product_ref: str
    stage: AttestationStage
    action_id: str
    execution_ref: str
    authority_semantics_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    evidence_reference_digests: tuple[str, ...]
    evaluated_at: datetime
    valid_until: datetime | None
    disposition: AttestationDisposition
    failure_reasons: tuple[str, ...] = ()
    attestation_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False
    can_determine_coverage: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"attestation_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_attestation(self) -> AgentRiskAttestation:
        if not self.profile_id or not self.insurer_ref or not self.product_ref:
            raise ValueError("agent risk attestation identity fields are required")
        if not self.action_id or not self.execution_ref:
            raise ValueError("agent risk attestation execution identity is required")
        if len(set(self.evidence_reference_digests)) != len(
            self.evidence_reference_digests
        ):
            raise ValueError("attestation evidence references must be unique")
        if self.disposition is AttestationDisposition.ATTESTED:
            if self.failure_reasons:
                raise ValueError("ATTESTED result cannot carry failure reasons")
            if self.valid_until is None or self.valid_until <= self.evaluated_at:
                raise ValueError("ATTESTED result requires a positive validity window")
        else:
            if not self.failure_reasons:
                raise ValueError("NOT_ATTESTED result requires failure reasons")
            if self.valid_until is not None:
                raise ValueError("NOT_ATTESTED result cannot claim a validity window")
        if self.attestation_digest and self.attestation_digest != self.computed_digest:
            raise ValueError("agent risk attestation digest mismatch")
        return self


def seal_assurance_evidence_reference(
    *,
    evidence_id: str,
    kind: AssuranceEvidenceKind,
    action_id: str,
    execution_ref: str,
    authority_semantics_digest: str,
    source_ref: str,
    evidence_digest: str,
    observed_at: datetime,
    valid_until: datetime,
    decision_outcome: str | None = None,
    effect_ref: str | None = None,
    assertions: tuple[str, ...] = (),
    contradictory: bool = False,
) -> AssuranceEvidenceReference:
    unsealed = AssuranceEvidenceReference(
        evidence_id=evidence_id,
        kind=kind,
        action_id=action_id,
        execution_ref=execution_ref,
        authority_semantics_digest=authority_semantics_digest,
        source_ref=source_ref,
        evidence_digest=evidence_digest,
        observed_at=observed_at,
        valid_until=valid_until,
        decision_outcome=decision_outcome,
        effect_ref=effect_ref,
        assertions=assertions,
        contradictory=contradictory,
    )
    return AssuranceEvidenceReference.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "reference_digest": unsealed.computed_digest,
        }
    )


def seal_agent_risk_control_profile(
    *,
    profile_id: str,
    insurer_ref: str,
    product_ref: str,
    effective_from: datetime,
    valid_until: datetime,
    required_pre_commit_evidence: tuple[AssuranceEvidenceKind, ...] | None = None,
    required_post_effect_evidence: tuple[AssuranceEvidenceKind, ...] | None = None,
    required_path_assertions: tuple[str, ...] | None = None,
    accepted_racs_outcomes: tuple[str, ...] | None = None,
    max_evidence_age_seconds: int = 900,
) -> AgentRiskControlProfile:
    data: dict[str, object] = {
        "profile_id": profile_id,
        "insurer_ref": insurer_ref,
        "product_ref": product_ref,
        "effective_from": effective_from,
        "valid_until": valid_until,
        "max_evidence_age_seconds": max_evidence_age_seconds,
    }
    if required_pre_commit_evidence is not None:
        data["required_pre_commit_evidence"] = required_pre_commit_evidence
    if required_post_effect_evidence is not None:
        data["required_post_effect_evidence"] = required_post_effect_evidence
    if required_path_assertions is not None:
        data["required_path_assertions"] = required_path_assertions
    if accepted_racs_outcomes is not None:
        data["accepted_racs_outcomes"] = accepted_racs_outcomes
    unsealed = AgentRiskControlProfile.model_validate(data)
    return AgentRiskControlProfile.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "profile_digest": unsealed.computed_digest,
        }
    )


def assess_agent_risk_attestation(
    *,
    profile: AgentRiskControlProfile,
    authority_semantics: PrincipalAuthoritySemantics,
    evidence: tuple[AssuranceEvidenceReference, ...],
    stage: AttestationStage,
    execution_ref: str,
    evaluated_at: datetime,
) -> AgentRiskAttestation:
    """Assess technical underwriting-control conformance without authorizing.

    Any missing, stale, mismatched, contradictory or ambiguous required
    evidence produces NOT_ATTESTED and no validity window.
    """

    if profile.profile_digest != profile.computed_digest:
        raise ValueError("agent risk control profile is unsealed or tampered")
    if authority_semantics.semantics_digest != authority_semantics.computed_digest:
        raise ValueError("principal authority semantics are unsealed or tampered")
    if not execution_ref:
        raise ValueError("execution_ref is required")

    reasons: list[str] = []
    action_id = authority_semantics.proposed_action.action_id

    if not (profile.effective_from <= evaluated_at < profile.valid_until):
        reasons.append("PROFILE_NOT_ACTIVE")
    if not (
        authority_semantics.evaluated_at
        <= evaluated_at
        < authority_semantics.valid_until
    ):
        reasons.append("AUTHORITY_SEMANTICS_NOT_FRESH")

    required_kinds = (
        profile.required_pre_commit_evidence
        if stage is AttestationStage.PRE_COMMIT
        else profile.required_post_effect_evidence
    )

    by_kind: dict[AssuranceEvidenceKind, list[AssuranceEvidenceReference]] = {}
    reference_digests: list[str] = []
    freshness_bounds: list[datetime] = [
        profile.valid_until,
        authority_semantics.valid_until,
    ]

    for item in evidence:
        by_kind.setdefault(item.kind, []).append(item)
        reference_digests.append(item.reference_digest)
        if not item.reference_digest or item.reference_digest != item.computed_digest:
            reasons.append(f"EVIDENCE_REFERENCE_TAMPERED:{item.evidence_id}")
        if item.action_id != action_id:
            reasons.append(f"ACTION_MISMATCH:{item.evidence_id}")
        if item.execution_ref != execution_ref:
            reasons.append(f"EXECUTION_MISMATCH:{item.evidence_id}")
        if item.authority_semantics_digest != authority_semantics.semantics_digest:
            reasons.append(f"AUTHORITY_BINDING_MISMATCH:{item.evidence_id}")
        if item.contradictory:
            reasons.append(f"CONTRADICTORY_EVIDENCE:{item.evidence_id}")
        if not (item.observed_at <= evaluated_at < item.valid_until):
            reasons.append(f"EVIDENCE_NOT_FRESH:{item.evidence_id}")
        max_age_bound = item.observed_at + timedelta(
            seconds=profile.max_evidence_age_seconds
        )
        freshness_bounds.extend((item.valid_until, max_age_bound))
        if evaluated_at >= max_age_bound:
            reasons.append(f"EVIDENCE_TOO_OLD:{item.evidence_id}")

    for kind in required_kinds:
        items = by_kind.get(kind, [])
        if not items:
            reasons.append(f"MISSING_REQUIRED_EVIDENCE:{kind.value}")
        elif len(items) > 1:
            reasons.append(f"AMBIGUOUS_REQUIRED_EVIDENCE:{kind.value}")

    racs_items = by_kind.get(AssuranceEvidenceKind.RACS_DECISION, [])
    if len(racs_items) == 1:
        outcome = racs_items[0].decision_outcome
        if outcome not in profile.accepted_racs_outcomes:
            reasons.append(f"RACS_OUTCOME_NOT_ACCEPTED:{outcome}")

    path_items = by_kind.get(AssuranceEvidenceKind.EFFECT_PATH_CONFORMANCE, [])
    if len(path_items) == 1:
        path_assertions = set(path_items[0].assertions)
        for assertion in profile.required_path_assertions:
            if assertion not in path_assertions:
                reasons.append(f"MISSING_PATH_ASSERTION:{assertion}")

    if stage is AttestationStage.POST_EFFECT:
        effect_refs = {
            item.effect_ref
            for item in evidence
            if item.kind
            in {
                AssuranceEvidenceKind.EFFECT_RECEIPT,
                AssuranceEvidenceKind.OUTCOME_EVIDENCE,
            }
            and item.effect_ref is not None
        }
        if len(effect_refs) != 1:
            reasons.append("EFFECT_CORRELATION_MISMATCH")

    reasons = list(dict.fromkeys(reasons))
    disposition = (
        AttestationDisposition.ATTESTED
        if not reasons
        else AttestationDisposition.NOT_ATTESTED
    )
    valid_until = min(freshness_bounds) if not reasons else None

    attestation_id = canonical_digest(
        {
            "profile_digest": profile.profile_digest,
            "authority_semantics_digest": authority_semantics.semantics_digest,
            "stage": stage.value,
            "action_id": action_id,
            "execution_ref": execution_ref,
            "evaluated_at": evaluated_at.isoformat(),
            "evidence_reference_digests": sorted(reference_digests),
        }
    )
    unsealed = AgentRiskAttestation(
        attestation_id=attestation_id,
        profile_id=profile.profile_id,
        profile_digest=profile.profile_digest,
        insurer_ref=profile.insurer_ref,
        product_ref=profile.product_ref,
        stage=stage,
        action_id=action_id,
        execution_ref=execution_ref,
        authority_semantics_digest=authority_semantics.semantics_digest,
        evidence_reference_digests=tuple(sorted(reference_digests)),
        evaluated_at=evaluated_at,
        valid_until=valid_until,
        disposition=disposition,
        failure_reasons=tuple(reasons),
    )
    return AgentRiskAttestation.model_validate(
        {
            **unsealed.model_dump(mode="python"),
            "attestation_digest": unsealed.computed_digest,
        }
    )
