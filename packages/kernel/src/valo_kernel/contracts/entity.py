from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .common import EntityType, normalize_extensible_type, utcnow
from .provenance import Provenance


class Entity(BaseModel):
    """Canonical kernel entity. Domain objects (Electrician, Patient, ...)
    come from registered packs, never from the kernel core."""

    entity_id: str
    entity_type: EntityType | str
    tenant_id: str
    legal_context: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    state: str | None = None
    valid_from: datetime = Field(default_factory=utcnow)
    valid_until: datetime | None = None
    version: int = 1
    provenance: Provenance

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("entity_type", mode="before")
    @classmethod
    def validate_entity_type(cls, value: Any) -> EntityType | str:
        return normalize_extensible_type(value, EntityType, label="entity_type")

    def is_active(self, moment: datetime | None = None) -> bool:
        moment = moment or utcnow()
        return self.valid_from <= moment and (
            self.valid_until is None or moment < self.valid_until
        )

