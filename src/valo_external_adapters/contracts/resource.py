from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import ResourceState, utcnow


class Resource(BaseModel):
    """Canonical resource: personnel, time, vehicles, equipment, money,
    inventory, capacity, slots."""

    resource_id: str
    resource_type: str
    tenant_id: str
    capacity: int = 1
    allocated: int = 0
    state: ResourceState = ResourceState.AVAILABLE
    holder: str | None = None
    attributes: dict[str, str] = Field(default_factory=dict)
    valid_until: datetime | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def check_capacity(self) -> Resource:
        if self.allocated < 0 or self.allocated > self.capacity:
            raise ValueError("allocated must be within [0, capacity]")
        if self.state == ResourceState.ALLOCATED and self.allocated >= self.capacity:
            raise ValueError("allocated cannot exceed capacity")
        return self

    @property
    def available(self) -> int:
        return max(0, self.capacity - self.allocated)

    def can_reserve(self) -> bool:
        return self.state == ResourceState.AVAILABLE and self.available > 0


class Reservation(BaseModel):
    """Atomic reservation: prevents parallel workflows from using the same
    resource. A resource can be reserved at most once while AVAILABLE."""

    reservation_id: str
    resource_id: str
    holder: str  # entity_id / actor
    tenant_id: str
    purpose: str | None = None
    quantity: int = 1
    valid_until: datetime | None = None
    status: str = "ACTIVE"  # ACTIVE | RELEASED | EXPIRED | CONSUMED

    model_config = ConfigDict(extra="forbid", frozen=True)

    def is_active(self, moment: datetime | None = None) -> bool:
        moment = moment or utcnow()
        return self.status == "ACTIVE" and (
            self.valid_until is None or moment < self.valid_until
        )
