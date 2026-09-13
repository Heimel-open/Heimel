"""LinkedIn draft adapter into the governed-media shadow contracts."""

from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import Field, model_validator

from .models import (
    ApprovalState,
    CandidateType,
    ChannelVariant,
    ClaimBinding,
    DigestRef,
    HandlingMode,
    MediaChannel,
    StrictModel,
    sha256_text,
)
from .shadow_loop import OpportunitySignal


class LinkedInDraftRequest(StrictModel):
    signal_id: str = Field(min_length=1)
    observed_at: datetime
    candidate_type: CandidateType = CandidateType.POST
    theme_key: str = Field(min_length=1)
    canonical_asset_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    account_identity: str = Field(min_length=1)
    audience_intent_id: str = Field(min_length=1)
    rendered_content: str = Field(min_length=1)
    source_refs: List[DigestRef] = Field(min_length=1)
    claim_bindings: List[ClaimBinding] = Field(default_factory=list)
    ai_production_disclosure: str = Field(min_length=1)
    why_now: str = Field(min_length=1)
    relationship_objective: str = Field(min_length=1)
    risk_class: str = Field(min_length=1)
    strategic_relevance: float = Field(ge=0.0, le=1.0)
    evidence_strength: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    timeliness: float = Field(ge=0.0, le=1.0)
    audience_fit: float = Field(ge=0.0, le=1.0)
    relationship_value: float = Field(ge=0.0, le=1.0)
    authority_risk: float = Field(ge=0.0, le=1.0)
    founder_effort_minutes: int = Field(ge=0)
    named_relationship: bool = False
    sensitive: bool = False

    @model_validator(mode="after")
    def prohibit_private_message_generation(self) -> "LinkedInDraftRequest":
        if self.candidate_type == CandidateType.PRIVATE_MESSAGE:
            raise ValueError("private-message generation is outside the governed LinkedIn adapter")
        return self


def build_linkedin_opportunity_signal(request: LinkedInDraftRequest) -> OpportunitySignal:
    handling_mode = (
        HandlingMode.DIRECT_HUMAN
        if request.named_relationship or request.sensitive
        else HandlingMode.BATCH_APPROVAL
    )
    variant = ChannelVariant(
        variant_id=f"linkedin:{request.signal_id}",
        canonical_asset_id=request.canonical_asset_id,
        campaign_id=request.campaign_id,
        channel=MediaChannel.LINKEDIN,
        account_identity=request.account_identity,
        rendered_content=request.rendered_content,
        rendered_content_digest=sha256_text(request.rendered_content),
        source_refs=request.source_refs,
        claim_bindings=request.claim_bindings,
        ai_production_disclosure=request.ai_production_disclosure,
        platform_constraints_checked=False,
        risk_class=request.risk_class,
        handling_mode=handling_mode,
        approval_state=ApprovalState.PENDING,
    )
    return OpportunitySignal(
        signal_id=request.signal_id,
        observed_at=request.observed_at,
        candidate_type=request.candidate_type,
        theme_key=request.theme_key,
        source_asset_id=request.canonical_asset_id,
        variant=variant,
        audience_intent_id=request.audience_intent_id,
        why_now=request.why_now,
        relationship_objective=request.relationship_objective,
        strategic_relevance=request.strategic_relevance,
        evidence_strength=request.evidence_strength,
        novelty=request.novelty,
        timeliness=request.timeliness,
        audience_fit=request.audience_fit,
        relationship_value=request.relationship_value,
        authority_risk=request.authority_risk,
        founder_effort_minutes=request.founder_effort_minutes,
        named_relationship=request.named_relationship,
        sensitive=request.sensitive,
    )


__all__ = ["LinkedInDraftRequest", "build_linkedin_opportunity_signal"]
