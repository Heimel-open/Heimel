from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import canonical_digest


class PersistentStateKind(str, Enum):
    MEMORY = "MEMORY"
    CONFIGURATION = "CONFIGURATION"
    INSTRUCTION = "INSTRUCTION"
    HANDOFF = "HANDOFF"
    ARTIFACT = "ARTIFACT"
    OTHER = "OTHER"


class PersistentStateBinding(BaseModel):
    schema_version: Literal["persistent_state_binding.v1"] = (
        "persistent_state_binding.v1"
    )
    persistent_ref: str
    state_kind: PersistentStateKind
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    workspace_id: str
    workspace_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_state_root: str = Field(pattern=r"^[0-9a-f]{64}$")
    source_ref: str
    source_object_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    purpose_id: str
    binding_digest: str = ""
    read_only: Literal[True] = True
    requires_fresh_admission: Literal[True] = True
    can_self_propagate: Literal[False] = False
    authority_effect: Literal["NO_AUTHORITY_CREATION"] = "NO_AUTHORITY_CREATION"
    can_issue_clearance: Literal[False] = False

    model_config = ConfigDict(extra="forbid", frozen=True)

    def canonical_payload(self) -> dict[str, Any]:
        return self.model_dump(mode="json", exclude={"binding_digest"})

    @property
    def computed_digest(self) -> str:
        return canonical_digest(self.canonical_payload())

    @model_validator(mode="after")
    def validate_binding(self) -> PersistentStateBinding:
        required = (
            self.persistent_ref,
            self.workspace_id,
            self.source_ref,
            self.purpose_id,
        )
        if any(not value for value in required):
            raise ValueError("persistent state context is required")
        if not self.source_ref.startswith("evidence:"):
            raise ValueError("persistent state must originate from admitted evidence")
        if self.binding_digest and self.binding_digest != self.computed_digest:
            raise ValueError("persistent state binding digest mismatch")
        return self
