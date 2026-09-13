from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class LegalBasis:
    """First-class legal basis: an explicit binding between an action and a
    home/materiell authority. Not a legal reasoning engine — the goal is the
    binding itself."""

    basis_id: str
    source: str
    provision: str
    valid_from: datetime
    valid_until: datetime | None = None
    jurisdiction: str = "NO"
    applies_to: list[str] = field(default_factory=list)
    permits: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)
    prohibits: list[str] = field(default_factory=list)
    rights_effect: list[str] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)

    def is_active(self, moment: datetime) -> bool:
        return self.valid_from <= moment and (self.valid_until is None or moment < self.valid_until)

    def permits_action(self, action_type: str, moment: datetime) -> bool:
        if not self.is_active(moment):
            return False
        return action_type in self.permits


@dataclass(frozen=True)
class Competence:
    """Competence: legal basis says an action is lawful in the abstract;
    competence says WHO may do it. A correct action by the wrong body/unit is
    invalid."""

    competence_id: str
    public_body: str
    unit: str
    capability: str
    scope: list[str] = field(default_factory=list)
    basis: str = ""
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    delegation_allowed: bool = False
    revoked: bool = False

    def is_active(self, moment: datetime) -> bool:
        return not (
            self.revoked
            or (self.valid_from is not None and moment < self.valid_from)
            or (self.valid_until is not None and moment >= self.valid_until)
        )

    def grants(self, body: str, unit: str, capability: str, scope: list[str], moment: datetime) -> bool:
        return bool(
            self.is_active(moment)
            and self.public_body == body
            and self.unit == unit
            and self.capability == capability
            and (not self.scope or set(scope).issubset(set(self.scope)) or "*" in self.scope)
        )


@dataclass(frozen=True)
class Delegation:
    """Delegation of competence. A delegation can never increase competence,
    widen geographic/sakstype scope, or survive revocation/parent expiry."""

    delegation_id: str
    delegator: str
    delegate: str
    competence_ref: str
    scope_reduction: list[str] = field(default_factory=list)
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    revoked: bool = False

    def scope_ok(self, requested_scope: list[str]) -> bool:
        if "*" in self.scope_reduction:
            return True
        return set(requested_scope).issubset(set(self.scope_reduction))

    def is_active(self, parent: Competence, moment: datetime) -> bool:
        return not (
            self.revoked
            or not parent.is_active(moment)
            or (self.valid_from is not None and moment < self.valid_from)
            or (self.valid_until is not None and moment >= self.valid_until)
        )
