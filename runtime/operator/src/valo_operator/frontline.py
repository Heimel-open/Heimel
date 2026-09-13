"""Provider-neutral frontline Work OS intake contracts.

Low-friction channels may capture text, photos and voice, but channel identity,
model confidence and captured knowledge are evidence only. Consequence-bearing
operations are converted into the existing OperatorRequest shape and therefore
still require the registered Function -> REHT -> Gateway path.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .api import OperatorRequest


class FrontlineModality(StrEnum):
    TEXT = "text"
    PHOTO = "photo"
    VOICE = "voice"


class FrontlineEnvelope(BaseModel):
    """Normalized input from SMS, voice, photo or another frontline channel.

    `channel_actor_ref` is correlation/evidence only. It is deliberately not an
    OperatorSession and cannot confer authority.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    interaction_id: str = Field(min_length=1)
    channel: str = Field(min_length=1)
    channel_actor_ref: str = Field(min_length=1)
    modality: FrontlineModality
    received_at: str = Field(min_length=1)
    locale: str | None = None
    text: str | None = None
    artifact_refs: tuple[str, ...] = Field(default_factory=tuple)
    authority_effect: Literal["none"] = "none"

    @model_validator(mode="after")
    def validate_payload(self) -> FrontlineEnvelope:
        has_text = bool(self.text and self.text.strip())
        if not has_text and not self.artifact_refs:
            raise ValueError("frontline input requires text or an artifact reference")
        if self.modality == FrontlineModality.TEXT and not has_text:
            raise ValueError("text modality requires text")
        if self.modality in {FrontlineModality.PHOTO, FrontlineModality.VOICE} and not self.artifact_refs:
            raise ValueError(f"{self.modality.value} modality requires an artifact reference")
        return self


class KnowledgeCandidate(BaseModel):
    """A candidate knowledge item captured from documents or human exchanges.

    Captured tribal knowledge never becomes timeless truth merely because a
    worker or manager supplied it. Provenance and a freshness boundary are
    mandatory before it can be admitted by a domain knowledge layer.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    knowledge_id: str = Field(min_length=1)
    source_interaction_id: str = Field(min_length=1)
    source_actor_ref: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    provenance_refs: tuple[str, ...] = Field(min_length=1)
    observed_at: str = Field(min_length=1)
    fresh_until: str = Field(min_length=1)
    verification_status: Literal["unverified", "corroborated", "verified"] = "unverified"
    authority_effect: Literal["none"] = "none"


class CandidateOperation(BaseModel):
    """A proposed frontline write/action bound to an already registered Function.

    There are intentionally no effect, risk, permission or authority override
    fields. Those remain properties of the registered Function and runtime
    execution context.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    correlation_id: str = Field(min_length=1)
    source_interaction_id: str = Field(min_length=1)
    function_id: str = Field(min_length=1)
    function_version: str = "1.0.0"
    inputs: dict[str, Any] = Field(default_factory=dict)
    route_hint: str | None = None
    requires_fresh_reht: Literal[True] = True
    authority_effect: Literal["none"] = "none"


def bind_candidate_operation(operation: CandidateOperation) -> OperatorRequest:
    """Compile a candidate operation into the canonical Operator request.

    This does not execute anything and does not create a session or permit.
    """

    return OperatorRequest(
        correlation_id=operation.correlation_id,
        function_id=operation.function_id,
        function_version=operation.function_version,
        inputs=operation.inputs,
    )
