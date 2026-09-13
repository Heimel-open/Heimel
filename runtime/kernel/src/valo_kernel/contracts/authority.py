from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import utcnow
from .time import TimeWindow


class Authority(BaseModel):
    """Canonical authority. Authority is data — never a role description in a
    prompt. Grants a principal a capability within a scope, with an explicit
    validity window and revocation state."""

    authority_id: str
    principal: str  # entity_id / actor
    capability: str  # e.g. "BOOK", "PAY", "ALLOCATE"
    scope: list[str] = Field(default_factory=list)  # resource scope
    constraints: dict[str, str] = Field(default_factory=dict)
    basis: str  # reference to the basis of the grant
    validity: TimeWindow
    delegable: bool = False
    revocable: bool = True
    status: str = "ACTIVE"  # ACTIVE | REVOKED | EXPIRED
    revoked_at: datetime | None = None
    revocation_ref: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def check_revocation(self) -> Authority:
        if self.revoked_at is not None and not self.revocation_ref:
            raise ValueError("revocation_ref is required when revoked_at is set")
        return self

    def is_active(self, moment: datetime | None = None) -> bool:
        moment = moment or utcnow()
        if self.status == "REVOKED":
            return False
        if self.revoked_at is not None and self.revoked_at <= moment:
            return False
        return self.validity.is_active_at(moment)


class Delegation(BaseModel):
    """Delegation of authority. A delegation can NEVER increase authority; it
    may only narrow scope or carry it forward."""

    delegation_id: str
    delegator: str
    delegate: str
    authority_ref: str
    scope_reduction: list[str] = Field(default_factory=list)  # subset of parent scope
    purpose_restriction: list[str] = Field(default_factory=list)
    validity: TimeWindow
    conditions: list[str] = Field(default_factory=list)
    revocable: bool = True
    revoked_at: datetime | None = None
    revocation_ref: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True)

    def is_active(self, moment: datetime | None = None) -> bool:
        moment = moment or utcnow()
        if self.revoked_at is not None and self.revoked_at <= moment:
            return False
        return self.validity.is_active_at(moment)
