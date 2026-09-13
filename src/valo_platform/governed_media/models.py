"""Strict contracts for governed media assets, candidates, decisions and outcomes."""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from hashlib import sha256
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, str_strip_whitespace=True)


class MediaChannel(str, Enum):
    WEBSITE_NEWSROOM = "website_newsroom"
    LINKEDIN = "linkedin"
    YOUTUBE = "youtube"
    PODCAST = "podcast"
    NEWSLETTER = "newsletter"
    X = "x"
    INSTAGRAM = "instagram"
    FACEBOOK = "facebook"
    SLACK = "slack"
    DISCORD = "discord"
    TWITCH = "twitch"


class AssetType(str, Enum):
    ARTICLE = "article"
    REPORT = "report"
    DEMO = "demo"
    VIDEO = "video"
    AUDIO = "audio"
    DIAGRAM = "diagram"
    RESEARCH_NOTE = "research_note"
    FOUNDER_NOTE = "founder_note"
    PRESS_PACK = "press_pack"
    OTHER = "other"


class FactualStatus(str, Enum):
    OBSERVED = "observed"
    VERIFIED = "verified"
    INFERRED = "inferred"
    ESTIMATED = "estimated"
    PROJECTED = "projected"


class Confidentiality(str, Enum):
    PRIVATE = "private"
    RESTRICTED = "restricted"
    INTERNAL = "internal"
    PUBLIC = "public"


class CandidateType(str, Enum):
    POST = "post"
    COMMENT = "comment"
    PRIVATE_MESSAGE = "private_message"


class HandlingMode(str, Enum):
    BATCH_APPROVAL = "batch_approval"
    DIRECT_HUMAN = "direct_human"
    BLOCKED = "blocked"


class ApprovalState(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    EDITED = "edited"
    PAUSED = "paused"
    REJECTED = "rejected"
    EVIDENCE_REQUESTED = "evidence_requested"
    ESCALATED = "escalated"


class ExecutionState(str, Enum):
    NOT_ATTEMPTED = "not_attempted"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    WITHDRAWN = "withdrawn"
    CORRECTED = "corrected"


class EngagementKind(str, Enum):
    NOISE = "noise"
    ACKNOWLEDGEMENT = "acknowledgement"
    SUBSTANTIVE_QUESTION = "substantive_question"
    CRITICISM = "criticism"
    OPPORTUNITY = "opportunity"
    PRESS = "press"
    PARTNER = "partner"
    CUSTOMER = "customer"
    INVESTOR = "investor"
    SAFETY = "safety"


class DigestRef(StrictModel):
    ref: str = Field(min_length=1)
    digest_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    version: Optional[str] = None


class ClaimBinding(StrictModel):
    claim_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    material: bool = True
    evidence_refs: List[DigestRef] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def material_claim_requires_evidence(self) -> "ClaimBinding":
        if self.material and not self.evidence_refs:
            raise ValueError("material claims require at least one evidence reference")
        return self


class AudienceIntent(StrictModel):
    audience_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    desired_action: str = Field(min_length=1)
    relationship_classes: List[str] = Field(default_factory=list)


class CampaignBrief(StrictModel):
    campaign_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    principal_idea: str = Field(min_length=1)
    owner_id: str = Field(min_length=1)
    brand_profile_version: str = Field(min_length=1)
    audiences: List[AudienceIntent] = Field(min_length=1)
    allowed_channels: List[MediaChannel] = Field(min_length=1)
    prohibited_actions: List[str] = Field(default_factory=list)


class CanonicalMediaAsset(StrictModel):
    asset_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    asset_type: AssetType
    owner_id: str = Field(min_length=1)
    source_refs: List[DigestRef] = Field(min_length=1)
    confidentiality: Confidentiality = Confidentiality.PRIVATE
    factual_status: FactualStatus
    allowed_audiences: List[str] = Field(default_factory=list)
    allowed_channels: List[MediaChannel] = Field(default_factory=list)
    prohibited_uses: List[str] = Field(default_factory=list)
    brand_profile_version: str = Field(min_length=1)
    campaign_ids: List[str] = Field(default_factory=list)
    review_due: Optional[date] = None
    withdrawn: bool = False
    correction_ref: Optional[DigestRef] = None

    @model_validator(mode="after")
    def public_asset_requires_explicit_scope(self) -> "CanonicalMediaAsset":
        if self.confidentiality == Confidentiality.PUBLIC:
            if not self.allowed_audiences or not self.allowed_channels:
                raise ValueError("public assets require explicit audiences and channels")
        if self.withdrawn and self.correction_ref is None:
            raise ValueError("withdrawn assets require a correction or withdrawal reference")
        return self


class ChannelVariant(StrictModel):
    variant_id: str = Field(min_length=1)
    canonical_asset_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    channel: MediaChannel
    account_identity: str = Field(min_length=1)
    rendered_content: str = Field(min_length=1)
    rendered_content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_refs: List[DigestRef] = Field(default_factory=list)
    source_refs: List[DigestRef] = Field(min_length=1)
    claim_bindings: List[ClaimBinding] = Field(default_factory=list)
    ai_production_disclosure: str = Field(min_length=1)
    platform_constraints_checked: bool = False
    requested_window_start: Optional[datetime] = None
    requested_window_end: Optional[datetime] = None
    risk_class: str = Field(min_length=1)
    handling_mode: HandlingMode = HandlingMode.BATCH_APPROVAL
    approval_state: ApprovalState = ApprovalState.PENDING
    clearance_ref: Optional[DigestRef] = None
    execution_ref: Optional[DigestRef] = None

    @model_validator(mode="after")
    def validate_exact_artifact_and_window(self) -> "ChannelVariant":
        expected = sha256_text(self.rendered_content)
        if self.rendered_content_digest != expected:
            raise ValueError("rendered_content_digest does not match rendered_content")
        if (
            self.requested_window_start is not None
            and self.requested_window_end is not None
            and self.requested_window_end < self.requested_window_start
        ):
            raise ValueError("publication window end cannot precede start")
        if self.approval_state in {ApprovalState.APPROVED, ApprovalState.EDITED}:
            if not self.platform_constraints_checked:
                raise ValueError("approved variants require platform constraint checks")
        return self


class PublicationCandidate(StrictModel):
    candidate_id: str = Field(min_length=1)
    candidate_type: CandidateType
    variant: ChannelVariant
    audience_intent_id: str = Field(min_length=1)
    why_now: str = Field(min_length=1)
    relationship_objective: str = Field(min_length=1)
    strategic_relevance: float = Field(ge=0.0, le=1.0)
    evidence_strength: float = Field(ge=0.0, le=1.0)
    novelty: float = Field(ge=0.0, le=1.0)
    timeliness: float = Field(ge=0.0, le=1.0)
    audience_fit: float = Field(ge=0.0, le=1.0)
    relationship_value: float = Field(ge=0.0, le=1.0)
    authority_risk: float = Field(ge=0.0, le=1.0)
    founder_effort_minutes: int = Field(ge=0)
    ranking_score: float = Field(ge=0.0, le=1.0)
    handling_mode: HandlingMode
    source_signal_ids: List[str] = Field(min_length=1)

    @model_validator(mode="after")
    def enforce_relationship_boundary(self) -> "PublicationCandidate":
        if self.candidate_type == CandidateType.PRIVATE_MESSAGE:
            raise ValueError("private-message candidates are prohibited in the automated queue")
        if self.variant.channel != MediaChannel.LINKEDIN:
            raise ValueError("the first shadow queue accepts LinkedIn variants only")
        return self


class PublicationDecision(StrictModel):
    decision_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    state: ApprovalState
    decided_by: str = Field(min_length=1)
    decided_at: datetime
    approved_variant_digest: Optional[str] = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    reason: Optional[str] = None

    @model_validator(mode="after")
    def approval_requires_exact_digest(self) -> "PublicationDecision":
        if self.state in {ApprovalState.APPROVED, ApprovalState.EDITED}:
            if self.approved_variant_digest is None:
                raise ValueError("approval requires an exact approved variant digest")
        return self


class PublicationExecutionRecord(StrictModel):
    execution_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    approved_variant_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    account_identity: str = Field(min_length=1)
    channel: MediaChannel
    connector_id: str = Field(min_length=1)
    state: ExecutionState
    attempted_at: datetime
    external_post_ref: Optional[str] = None
    clearance_ref: Optional[DigestRef] = None
    receipt_ref: Optional[DigestRef] = None
    error: Optional[str] = None

    @model_validator(mode="after")
    def success_requires_external_proof(self) -> "PublicationExecutionRecord":
        if self.state == ExecutionState.SUCCEEDED:
            if not self.external_post_ref or not self.clearance_ref or not self.receipt_ref:
                raise ValueError("successful publication requires external ref, clearance and receipt")
        if self.state == ExecutionState.FAILED and not self.error:
            raise ValueError("failed publication requires an error")
        return self


class EngagementSignal(StrictModel):
    signal_id: str = Field(min_length=1)
    external_post_ref: str = Field(min_length=1)
    observed_at: datetime
    kind: EngagementKind
    actor_ref: Optional[str] = None
    content_excerpt: Optional[str] = None
    qualified: bool = False
    requires_direct_human: bool = False
    resulting_action_ref: Optional[str] = None


class MediaOutcomeRecord(StrictModel):
    outcome_id: str = Field(min_length=1)
    campaign_id: str = Field(min_length=1)
    asset_id: str = Field(min_length=1)
    channel: MediaChannel
    observed_at: datetime
    qualified_replies: int = Field(default=0, ge=0)
    meetings: int = Field(default=0, ge=0)
    pilot_requests: int = Field(default=0, ge=0)
    partner_introductions: int = Field(default=0, ge=0)
    research_validation_actions: int = Field(default=0, ge=0)
    press_opportunities: int = Field(default=0, ge=0)
    evidence_refs: List[DigestRef] = Field(default_factory=list)


class FounderTimeRecord(StrictModel):
    record_date: date
    channel: MediaChannel
    baseline_manual_minutes: int = Field(ge=0)
    review_minutes: int = Field(ge=0)
    relationship_minutes: int = Field(ge=0)
    automated_production_minutes_avoided: int = Field(ge=0)
    rejected_or_reworked_candidates: int = Field(default=0, ge=0)
    resulting_qualified_actions: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def reject_synthetic_time_savings(self) -> "FounderTimeRecord":
        observed_remaining = self.review_minutes + self.relationship_minutes
        maximum_observable_saving = max(0, self.baseline_manual_minutes - observed_remaining)
        if self.automated_production_minutes_avoided != maximum_observable_saving:
            raise ValueError(
                "automated time avoided must equal baseline minus observed review and relationship minutes"
            )
        return self

    @property
    def automation_rate(self) -> float:
        if self.baseline_manual_minutes == 0:
            return 0.0
        return round(self.automated_production_minutes_avoided / self.baseline_manual_minutes, 6)


def sha256_text(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()


__all__ = [
    "ApprovalState",
    "AssetType",
    "AudienceIntent",
    "CampaignBrief",
    "CandidateType",
    "CanonicalMediaAsset",
    "ChannelVariant",
    "ClaimBinding",
    "Confidentiality",
    "DigestRef",
    "EngagementKind",
    "EngagementSignal",
    "ExecutionState",
    "FactualStatus",
    "FounderTimeRecord",
    "HandlingMode",
    "MediaChannel",
    "MediaOutcomeRecord",
    "PublicationCandidate",
    "PublicationDecision",
    "PublicationExecutionRecord",
    "sha256_text",
]
