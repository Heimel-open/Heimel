from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .common import RelationType, normalize_extensible_type, utcnow
from .time import TimeWindow


class Relationship(BaseModel):
    """A typed relationship in the relationship graph. Relationships are state,
    not LLM memory. Registered packs may add namespaced relation types."""

    relationship_id: str
    source: str
    relation_type: RelationType | str
    target: str
    tenant_id: str
    validity: TimeWindow
    basis: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)
    version: int = 1

    model_config = ConfigDict(extra="forbid", frozen=True)

    @field_validator("relation_type", mode="before")
    @classmethod
    def validate_relation_type(cls, value: Any) -> RelationType | str:
        return normalize_extensible_type(
            value,
            RelationType,
            label="relation_type",
        )

    @model_validator(mode="after")
    def check_distinct(self) -> Relationship:
        if self.source == self.target:
            raise ValueError("source and target must differ")
        return self

    def is_active(self, moment: datetime | None = None) -> bool:
        moment = moment or utcnow()
        return self.validity.is_active_at(moment)
