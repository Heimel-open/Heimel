"""Canonical Advisor Fabric schemas.

These models are intentionally non-runtime and non-authoritative. They define
the contract for Advisor profiles, interpretations, recommendations and action
case drafts before any migration of legacy Advisor/Advisor surfaces.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AdvisorAuthorityBoundary(str, Enum):
    """Authority boundary for every Advisor Fabric artifact."""

    ADVISORY_ONLY = "advisory_only"


class AdvisorMemoryPolicy(str, Enum):
    """Memory policy declared by an advisor profile."""

    NONE = "none"
    SESSION = "session"
    TENANT_SCOPED = "tenant_scoped"


class AdvisorRecommendationType(str, Enum):
    """Non-binding advisor output types."""

    INSIGHT = "insight"
    BRIEFING = "briefing"
    RECOMMENDATION = "recommendation"
    ACTION_CASE_DRAFT = "action_case_draft"


class AdvisorProfile(BaseModel):
    """Versioned role profile for one advisory colleague."""

    advisor_id: str = Field(..., description="Stable advisor identifier")
    version: str = Field(..., description="Immutable profile version")
    role: str = Field(..., description="Role lens, such as cfo, ciso or sustainability")
    purpose: str = Field(..., description="Non-authoritative advisory purpose")
    allowed_inputs: List[str] = Field(default_factory=list)
    allowed_outputs: List[AdvisorRecommendationType] = Field(default_factory=list)
    evidence_policy: str = Field(..., description="Evidence requirements for advisory output")
    memory_policy: AdvisorMemoryPolicy = AdvisorMemoryPolicy.NONE
    authority_boundary: Literal[AdvisorAuthorityBoundary.ADVISORY_ONLY] = (
        AdvisorAuthorityBoundary.ADVISORY_ONLY
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=False)


class AdvisorInterpretation(BaseModel):
    """Advisor interpretation of evidence from a role-specific lens."""

    interpretation_id: str
    advisor_id: str
    source_evidence_refs: List[str] = Field(default_factory=list)
    lineage_id: Optional[str] = None
    stance: str = Field(..., description="Advisor stance or reading of the evidence")
    confidence: float = Field(..., ge=0.0, le=1.0)
    limitations: List[str] = Field(default_factory=list)
    questions_for_human: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    authority_boundary: Literal[AdvisorAuthorityBoundary.ADVISORY_ONLY] = (
        AdvisorAuthorityBoundary.ADVISORY_ONLY
    )

    model_config = ConfigDict(use_enum_values=False)


class AdvisorRecommendation(BaseModel):
    """Non-binding advisor recommendation or briefing."""

    recommendation_id: str
    advisor_id: str
    source_interpretation_refs: List[str] = Field(default_factory=list)
    recommendation_type: AdvisorRecommendationType
    statement: str
    rationale: str
    risk_notes: List[str] = Field(default_factory=list)
    requires_action_case: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)
    authority_boundary: Literal[AdvisorAuthorityBoundary.ADVISORY_ONLY] = (
        AdvisorAuthorityBoundary.ADVISORY_ONLY
    )

    model_config = ConfigDict(use_enum_values=False)

    @model_validator(mode="after")
    def _action_case_type_requires_flag(self) -> "AdvisorRecommendation":
        if (
            self.recommendation_type == AdvisorRecommendationType.ACTION_CASE_DRAFT
            and not self.requires_action_case
        ):
            raise ValueError("action_case_draft recommendations must require an action case")
        return self


class ActionCaseDraft(BaseModel):
    """Advisor-prepared input for later VAIG evaluation.

    This is not an ActionEnvelope, clearance artifact or execution permit. It
    carries a proposed action summary and missing inputs so another boundary can
    decide whether a governed action should be assembled and evaluated.
    """

    draft_id: str
    originating_advisor_refs: List[str] = Field(default_factory=list)
    evidence_refs: List[str] = Field(default_factory=list)
    proposed_action_summary: str
    known_constraints: List[str] = Field(default_factory=list)
    missing_inputs: List[str] = Field(default_factory=list)
    handoff_target: Literal["VAIG"] = "VAIG"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    authority_boundary: Literal[AdvisorAuthorityBoundary.ADVISORY_ONLY] = (
        AdvisorAuthorityBoundary.ADVISORY_ONLY
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(use_enum_values=False)
