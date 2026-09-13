from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol, Sequence

import rfc8785
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .canonical import to_json_value


FORBIDDEN_MEMORY_TYPES = {
    "legal_mandate",
    "delegation",
    "human_approval",
    "policy_state",
    "admissibility_determination",
    "governance_clearance",
    "execution_receipt",
    "outcome_evidence",
}


class MemoryStatus(str, Enum):
    WORKING = "working"
    CANDIDATE = "candidate"
    VALIDATED = "validated"
    QUARANTINED = "quarantined"
    SUPERSEDED = "superseded"
    PURGED = "purged"


class MemoryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    memory_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    provider_ref: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    memory_type: str = Field(min_length=1)
    content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    source_refs: tuple[str, ...] = ()
    principal_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    created_at: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    status: MemoryStatus
    retention_class: str = Field(min_length=1)

    @field_validator("memory_type")
    @classmethod
    def reject_authoritative_objects(cls, value: str) -> str:
        if value in FORBIDDEN_MEMORY_TYPES:
            raise ValueError(f"authoritative object cannot be mutable memory: {value}")
        return value


class MemoryMutationEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    event_id: str = Field(min_length=1)
    operation: str = Field(min_length=1)
    memory_id: str = Field(min_length=1)
    snapshot_id: str = Field(min_length=1)
    branch: str = Field(min_length=1)
    principal_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    occurred_at: datetime
    content_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


def canonical_digest(payload: Any) -> str:
    canonical = rfc8785.dumps(to_json_value(payload))
    return f"sha256:{hashlib.sha256(canonical).hexdigest()}"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MemoryProvider(Protocol):
    async def create_snapshot(self, branch: str) -> str: ...
    async def create_branch(self, branch: str, from_snapshot: str | None = None) -> str: ...
    async def store_memory(self, *, content: Any, metadata: dict[str, Any]) -> MemoryRecord: ...
    async def retrieve_memory(self, memory_id: str) -> MemoryRecord | None: ...
    async def search_memory(self, query: str, *, branch: str, limit: int = 20) -> Sequence[MemoryRecord]: ...
    async def diff_branch(self, branch: str, against: str) -> dict[str, Any]: ...
    async def merge_branch(self, branch: str, target: str) -> str: ...
    async def rollback_branch(self, branch: str, snapshot_id: str) -> str: ...
    async def quarantine_memory(self, memory_id: str, reason: str) -> MemoryRecord: ...
    async def purge_memory(self, memory_id: str, reason: str) -> MemoryMutationEvent: ...
    async def health(self) -> dict[str, Any]: ...
