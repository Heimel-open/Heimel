from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import normalize_extensible_type, utcnow


class EventType(str, Enum):
    ENTITY_REGISTERED = "ENTITY_REGISTERED"
    ENTITY_UPDATED = "ENTITY_UPDATED"
    ENTITY_SUPERSEDED = "ENTITY_SUPERSEDED"
    ENTITY_REVOKED = "ENTITY_REVOKED"
    IDENTITY_CLAIMED = "IDENTITY_CLAIMED"
    IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
    IDENTITY_REVOKED = "IDENTITY_REVOKED"
    RELATIONSHIP_ESTABLISHED = "RELATIONSHIP_ESTABLISHED"
    RELATIONSHIP_TERMINATED = "RELATIONSHIP_TERMINATED"
    FACT_ASSERTED = "FACT_ASSERTED"
    FACT_ADMITTED = "FACT_ADMITTED"
    FACT_CONFIRMED = "FACT_CONFIRMED"
    FACT_SUPERSEDED = "FACT_SUPERSEDED"
    FACT_REVOKED = "FACT_REVOKED"
    FACT_CONFLICTED = "FACT_CONFLICTED"
    EVIDENCE_RECEIVED = "EVIDENCE_RECEIVED"
    STATE_ADMISSION_DECIDED = "STATE_ADMISSION_DECIDED"
    EVIDENCE_ADMITTED = "EVIDENCE_ADMITTED"
    EVIDENCE_REJECTED = "EVIDENCE_REJECTED"
    EVIDENCE_SUPERSEDED = "EVIDENCE_SUPERSEDED"
    AUTHORITY_GRANTED = "AUTHORITY_GRANTED"
    AUTHORITY_REVOKED = "AUTHORITY_REVOKED"
    DELEGATION_GRANTED = "DELEGATION_GRANTED"
    DELEGATION_REVOKED = "DELEGATION_REVOKED"
    RIGHT_GRANTED = "RIGHT_GRANTED"
    RIGHT_REVOKED = "RIGHT_REVOKED"
    OBLIGATION_CREATED = "OBLIGATION_CREATED"
    OBLIGATION_SATISFIED = "OBLIGATION_SATISFIED"
    OBLIGATION_FAILED = "OBLIGATION_FAILED"
    PURPOSE_REGISTERED = "PURPOSE_REGISTERED"
    PURPOSE_REVOKED = "PURPOSE_REVOKED"
    RESOURCE_REGISTERED = "RESOURCE_REGISTERED"
    RESOURCE_RESERVED = "RESOURCE_RESERVED"
    RESOURCE_ALLOCATED = "RESOURCE_ALLOCATED"
    RESOURCE_RELEASED = "RESOURCE_RELEASED"
    RESOURCE_CONSUMED = "RESOURCE_CONSUMED"
    RESOURCE_UNAVAILABLE = "RESOURCE_UNAVAILABLE"
    CONTRACT_SIGNED = "CONTRACT_SIGNED"
    CONTRACT_AMENDED = "CONTRACT_AMENDED"
    CONTRACT_TERMINATED = "CONTRACT_TERMINATED"
    RESERVATION_RELEASED = "RESERVATION_RELEASED"
    RESERVATION_EXPIRED = "RESERVATION_EXPIRED"
    RESERVATION_CONSUMED = "RESERVATION_CONSUMED"
    EXECUTION_PHASE_UPDATED = "EXECUTION_PHASE_UPDATED"
    CORRECTION = "CORRECTION"
    EXTERNAL_EFFECT_OBSERVED = "EXTERNAL_EFFECT_OBSERVED"
    DIVERGENCE_RECORDED = "DIVERGENCE_RECORDED"
    TRANSITION_VALIDATED = "TRANSITION_VALIDATED"


class CanonicalEvent(BaseModel):
    """Append-only canonical event. Registered packs may add namespaced event
    types, but the Kernel still seals, validates and applies every event."""

    event_id: str
    event_type: EventType | str
    tenant_id: str
    subject: str
    actor: str | None = None
    timestamp: datetime = Field(default_factory=utcnow)
    effective_at: datetime = Field(default_factory=utcnow)
    source: str
    payload: dict[str, Any] = Field(default_factory=dict)
    evidence_refs: list[str] = Field(default_factory=list)
    causation_id: str | None = None
    correlation_id: str | None = None
    idempotency_key: str | None = None
    sequence: int | None = None
    previous_hash: str | None = None
    event_hash: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    BACKDATING_TYPES: ClassVar[frozenset[EventType]] = frozenset(
        {EventType.CORRECTION, EventType.FACT_CONFLICTED}
    )
    CLOCK_SKEW: ClassVar = 2

    @field_validator("event_type", mode="before")
    @classmethod
    def validate_event_type(cls, value: Any) -> EventType | str:
        return normalize_extensible_type(value, EventType, label="event_type")

    @model_validator(mode="after")
    def check_time_order(self) -> CanonicalEvent:
        skew = self.effective_at - self.timestamp
        if (
            skew < -timedelta(seconds=self.CLOCK_SKEW)
            and self.event_type not in self.BACKDATING_TYPES
        ):
            raise ValueError(
                "effective_at must not precede timestamp unless it is a correction"
            )
        return self

