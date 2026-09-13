"""Shared Advisor Fabric conversation and mentor service."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Mapping, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .context_gateway import AdvisorContextPackage
from .profiles import get_advisor_profile
from .schemas import AdvisorAuthorityBoundary


class AdvisorConversationRole(str, Enum):
    """Conversation participant role."""

    HUMAN = "human"
    ADVISOR = "advisor"
    SYSTEM = "system"


class AdvisorConversationTurn(BaseModel):
    """One turn in an Advisor Fabric conversation."""

    turn_id: str
    role: AdvisorConversationRole
    content: str
    artifact_refs: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    authority_boundary: AdvisorAuthorityBoundary = AdvisorAuthorityBoundary.ADVISORY_ONLY

    model_config = ConfigDict(use_enum_values=False)

    @model_validator(mode="after")
    def _content_must_not_be_empty(self) -> "AdvisorConversationTurn":
        if not self.content.strip():
            raise ValueError("conversation turn content cannot be empty")
        return self


class AdvisorConversationSession(BaseModel):
    """Conversation session around one advisor and context package."""

    session_id: str
    advisor_id: str
    role: str
    context_package_id: str
    turns: Tuple[AdvisorConversationTurn, ...] = Field(default_factory=tuple)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    authority_boundary: AdvisorAuthorityBoundary = AdvisorAuthorityBoundary.ADVISORY_ONLY

    model_config = ConfigDict(use_enum_values=False)


class AdvisorConversationService:
    """Create and append advisory conversation sessions."""

    def start_session(
        self,
        *,
        session_id: str,
        context_package: AdvisorContextPackage,
        initial_human_message: str,
    ) -> AdvisorConversationSession:
        profile = get_advisor_profile(context_package.role)
        if profile.advisor_id != context_package.advisor_id:
            raise ValueError("context package advisor does not match registered profile")

        return AdvisorConversationSession(
            session_id=session_id,
            advisor_id=context_package.advisor_id,
            role=context_package.role,
            context_package_id=context_package.package_id,
            turns=(
                AdvisorConversationTurn(
                    turn_id=f"{session_id}:turn-1",
                    role=AdvisorConversationRole.HUMAN,
                    content=initial_human_message,
                ),
            ),
        )

    def append_turn(
        self,
        session: AdvisorConversationSession,
        *,
        turn_id: str,
        role: AdvisorConversationRole,
        content: str,
        artifact_refs: Optional[List[str]] = None,
    ) -> AdvisorConversationSession:
        turn = AdvisorConversationTurn(
            turn_id=turn_id,
            role=role,
            content=content,
            artifact_refs=list(artifact_refs or ()),
        )
        return session.model_copy(update={"turns": session.turns + (turn,)})

    def mentor_prompt(
        self,
        session: AdvisorConversationSession,
        *,
        objective: str,
        known_constraints: Optional[List[str]] = None,
        artifact_refs: Optional[List[str]] = None,
    ) -> AdvisorConversationTurn:
        constraints = "; ".join(known_constraints or ())
        content = (
            f"Mentor objective: {objective}. "
            "Stay advisory-only and route consequential proposals through ActionCaseDraft."
        )
        if constraints:
            content = f"{content} Constraints: {constraints}."
        return AdvisorConversationTurn(
            turn_id=f"{session.session_id}:mentor-{len(session.turns) + 1}",
            role=AdvisorConversationRole.SYSTEM,
            content=content,
            artifact_refs=list(artifact_refs or ()),
        )

    @staticmethod
    def summarize_session(session: AdvisorConversationSession) -> Mapping[str, object]:
        """Return a compact non-authoritative session summary."""

        return {
            "session_id": session.session_id,
            "advisor_id": session.advisor_id,
            "role": session.role,
            "context_package_id": session.context_package_id,
            "turn_count": len(session.turns),
            "artifact_refs": sorted(
                {
                    artifact_ref
                    for turn in session.turns
                    for artifact_ref in turn.artifact_refs
                }
            ),
            "authority_boundary": session.authority_boundary.value,
        }
