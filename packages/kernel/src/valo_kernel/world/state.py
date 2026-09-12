from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from ..contracts.admission import AdmissionDecision
from ..contracts.authority import Authority, Delegation
from ..contracts.common import SCHEMA_VERSION
from ..contracts.constraint import Constraint
from ..contracts.contract import Contract
from ..contracts.entity import Entity
from ..contracts.evidence import Evidence
from ..contracts.fact import Fact
from ..contracts.identity import IdentityClaim
from ..contracts.obligations import Obligation
from ..contracts.provenance import Provenance
from ..contracts.purpose import Purpose
from ..contracts.relationship import Relationship
from ..contracts.resource import Reservation, Resource
from ..contracts.rights import Right
from ..kernel.integrity import state_root_digest


class WorldState(BaseModel):
    """The working state of the governed world. Mutable by design: reducers
    apply canonical events deterministically to move from one state to the next.
    Never exposed directly as a contract."""

    schema_version: str = SCHEMA_VERSION
    tenant_id: str = "default"
    entities: dict[str, Entity] = Field(default_factory=dict)
    identities: dict[str, IdentityClaim] = Field(default_factory=dict)
    relationships: dict[str, Relationship] = Field(default_factory=dict)
    facts: dict[str, Fact] = Field(default_factory=dict)
    evidence: dict[str, Evidence] = Field(default_factory=dict)
    admissions: dict[str, AdmissionDecision] = Field(default_factory=dict)
    authorities: dict[str, Authority] = Field(default_factory=dict)
    delegations: dict[str, Delegation] = Field(default_factory=dict)
    rights: dict[str, Right] = Field(default_factory=dict)
    obligations: dict[str, Obligation] = Field(default_factory=dict)
    purposes: dict[str, Purpose] = Field(default_factory=dict)
    contracts: dict[str, Contract] = Field(default_factory=dict)
    constraints: dict[str, Constraint] = Field(default_factory=dict)
    resources: dict[str, Resource] = Field(default_factory=dict)
    reservations: dict[str, Reservation] = Field(default_factory=dict)
    active_process_refs: list[str] = Field(default_factory=list)
    clocks: dict[str, Any] = Field(default_factory=dict)
    provenance: dict[str, Provenance] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    def root_hash(self) -> str:
        return state_root_digest(self)

    def clone(self) -> WorldState:
        return self.model_copy(deep=True)

