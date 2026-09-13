"""Canonical shadow contracts for VALO Governed Newsroom."""

from __future__ import annotations

from enum import Enum
from typing import Dict, List

from pydantic import BaseModel, ConfigDict, Field

from src.valo_platform.models.core_receipt import ExecutionDecision
from src.valo_platform.verification_factory import (
    EvidenceAdmissibilityRecord,
    EvidencePackage,
    FactoryPreconditionResult,
    IntegrityPreconditionResult,
    PublicIntegrityCard,
    VerificationFinding,
    VersionedRef,
)


class NewsroomActionType(str, Enum):
    RESEARCH_USE = "RESEARCH_USE"
    DRAFT = "DRAFT"
    MATERIAL_REWRITE = "MATERIAL_REWRITE"
    HEADLINE = "HEADLINE"
    IMAGE = "IMAGE"
    AUDIO = "AUDIO"
    VIDEO = "VIDEO"
    TRANSLATION = "TRANSLATION"
    SUMMARY = "SUMMARY"
    PERSONALISATION = "PERSONALISATION"
    PUBLICATION = "PUBLICATION"
    NOTIFICATION = "NOTIFICATION"
    SOCIAL_DISTRIBUTION = "SOCIAL_DISTRIBUTION"
    SYNDICATION = "SYNDICATION"
    CORRECTION = "CORRECTION"
    RETRACTION = "RETRACTION"
    TRAINING_DATA_USE = "TRAINING_DATA_USE"


class NewsroomRiskTier(str, Enum):
    LOW = "LOW"
    MATERIAL = "MATERIAL"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class NewsroomGovernanceInputs(BaseModel):
    """Exact non-evidentiary governance inputs required around the package."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sol_context_ref: VersionedRef
    mal_model_admissibility_ref: VersionedRef
    proposed_artifact_ref: VersionedRef
    publication_authority_ref: VersionedRef
    action_type: NewsroomActionType
    risk_tier: NewsroomRiskTier
    accountable_editor_id: str
    human_review_completed: bool = False


class NewsroomShadowEvaluation(BaseModel):
    """Replayable shadow output. It is not GovernanceClearance."""

    model_config = ConfigDict(extra="forbid")

    case_id: str
    claim_id: str
    source_ids: List[str] = Field(default_factory=list)
    governance_inputs: NewsroomGovernanceInputs
    source_preconditions: Dict[str, IntegrityPreconditionResult] = Field(default_factory=dict)
    claim_preconditions: FactoryPreconditionResult
    report_findings: List[VerificationFinding] = Field(default_factory=list)
    admissibility: EvidenceAdmissibilityRecord
    evidence_package: EvidencePackage
    public_integrity_cards: List[PublicIntegrityCard] = Field(default_factory=list)
    shadow_reht_recommendation: ExecutionDecision
    recommendation_reasons: List[str] = Field(default_factory=list)
    required_conditions: List[str] = Field(default_factory=list)
    prohibited_uses: List[str] = Field(default_factory=list)
    metrics: Dict[str, float] = Field(default_factory=dict)


__all__ = [
    "NewsroomActionType",
    "NewsroomGovernanceInputs",
    "NewsroomRiskTier",
    "NewsroomShadowEvaluation",
]
