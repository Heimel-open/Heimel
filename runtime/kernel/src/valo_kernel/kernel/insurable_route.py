from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..contracts.common import canonical_digest


class InsurabilityOutcome(str, Enum):
    ASSESSABLE = "ASSESSABLE"
    NOT_ASSESSABLE = "NOT_ASSESSABLE"


class RiskBand(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    UNPRICED = "UNPRICED"


class InsurableRouteEvidence(BaseModel):
    schema_version: Literal["insurable_route_evidence.v0"] = "insurable_route_evidence.v0"
    route_evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    route_passed: bool
    reht_evaluation_id: str
    consequence_authorized: bool
    authority_fresh_at_consequence: bool
    receipt_digest: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    receipt_verified: bool
    consequence_limit_minor_units: int | None = Field(default=None, ge=0)
    provider_trust_domain: str
    execution_replayable: bool
    state_integrity_verified: bool
    evidence_digest: str = ""
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"evidence_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_evidence(self) -> "InsurableRouteEvidence":
        if not self.reht_evaluation_id or not self.provider_trust_domain:
            raise ValueError("REHT evaluation and provider trust domain are required")
        if self.receipt_verified and self.receipt_digest is None:
            raise ValueError("verified receipt requires a receipt digest")
        if self.evidence_digest and self.evidence_digest != self.computed_digest:
            raise ValueError("insurable route evidence digest mismatch")
        return self


class InsurableRouteAssessment(BaseModel):
    schema_version: Literal["insurable_route_assessment.v0"] = "insurable_route_assessment.v0"
    evidence_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    outcome: InsurabilityOutcome
    risk_band: RiskBand
    risk_score: int | None = Field(default=None, ge=0, le=100)
    blockers: tuple[str, ...] = ()
    risk_factors: tuple[str, ...] = ()
    assessment_digest: str = ""
    pricing_effect: Literal["SIGNAL_ONLY"] = "SIGNAL_ONLY"
    insurer_decision: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json", exclude={"assessment_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_assessment(self) -> "InsurableRouteAssessment":
        if self.outcome is InsurabilityOutcome.NOT_ASSESSABLE:
            if not self.blockers or self.risk_score is not None or self.risk_band is not RiskBand.UNPRICED:
                raise ValueError("unassessable route must be blocked and unpriced")
        else:
            if self.blockers or self.risk_score is None or self.risk_band is RiskBand.UNPRICED:
                raise ValueError("assessable route needs a priced signal and no blockers")
        if self.assessment_digest and self.assessment_digest != self.computed_digest:
            raise ValueError("insurable route assessment digest mismatch")
        return self


def seal_insurable_route_evidence(**values: object) -> InsurableRouteEvidence:
    provisional = InsurableRouteEvidence(**values)
    return provisional.model_copy(update={"evidence_digest": provisional.computed_digest})


def assess_insurable_route(evidence: InsurableRouteEvidence) -> InsurableRouteAssessment:
    if evidence.evidence_digest != evidence.computed_digest:
        raise ValueError("insurable route evidence is unsealed or tampered")

    blockers: list[str] = []
    if not evidence.route_passed:
        blockers.append("ROUTE_NOT_ADMISSIBLE")
    if not evidence.consequence_authorized:
        blockers.append("CONSEQUENCE_NOT_AUTHORIZED")
    if not evidence.authority_fresh_at_consequence:
        blockers.append("AUTHORITY_NOT_FRESH")
    if evidence.receipt_digest is None or not evidence.receipt_verified:
        blockers.append("VERIFIED_RECEIPT_MISSING")
    if evidence.consequence_limit_minor_units is None:
        blockers.append("CONSEQUENCE_UNBOUNDED")
    if not evidence.state_integrity_verified:
        blockers.append("STATE_INTEGRITY_UNVERIFIED")

    if blockers:
        provisional = InsurableRouteAssessment(
            evidence_digest=evidence.evidence_digest,
            outcome=InsurabilityOutcome.NOT_ASSESSABLE,
            risk_band=RiskBand.UNPRICED,
            blockers=tuple(blockers),
        )
        return provisional.model_copy(
            update={"assessment_digest": provisional.computed_digest}
        )

    score = 0
    factors: list[str] = []
    trust_domain = evidence.provider_trust_domain.lower()
    if trust_domain in {"sovereign", "local", "principal"}:
        pass
    elif trust_domain in {"managed", "enterprise"}:
        score += 5
        factors.append("MANAGED_EXTERNALITY")
    elif trust_domain == "external":
        score += 15
        factors.append("EXTERNAL_PROVIDER")
    else:
        score += 25
        factors.append("UNKNOWN_TRUST_DOMAIN")

    assert evidence.consequence_limit_minor_units is not None
    if evidence.consequence_limit_minor_units > 1_000_000:
        score += 15
        factors.append("HIGH_CONSEQUENCE_LIMIT")
    elif evidence.consequence_limit_minor_units > 100_000:
        score += 5
        factors.append("MATERIAL_CONSEQUENCE_LIMIT")

    if not evidence.execution_replayable:
        score += 20
        factors.append("EXECUTION_NOT_REPLAYABLE")

    score = min(score, 100)
    if score < 20:
        band = RiskBand.LOW
    elif score < 50:
        band = RiskBand.MODERATE
    else:
        band = RiskBand.HIGH

    provisional = InsurableRouteAssessment(
        evidence_digest=evidence.evidence_digest,
        outcome=InsurabilityOutcome.ASSESSABLE,
        risk_band=band,
        risk_score=score,
        risk_factors=tuple(factors),
    )
    return provisional.model_copy(update={"assessment_digest": provisional.computed_digest})
