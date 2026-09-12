from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .time import TimeWindow


class Contract(BaseModel):
    """Minimal state-basis representation of a contract. A full contract engine
    is out of scope; this is the state ground."""

    contract_id: str
    parties: list[str]
    tenant_id: str
    effective_period: TimeWindow
    rights: list[str] = Field(default_factory=list)  # right_ids
    obligations: list[str] = Field(default_factory=list)  # obligation_ids
    constraints: list[str] = Field(default_factory=list)  # constraint_ids
    price_rules_ref: str | None = None
    sla_refs: list[str] = Field(default_factory=list)
    authority_effects: list[str] = Field(default_factory=list)  # authority_ids
    version: int = 1
    status: str = "SIGNED"  # SIGNED | AMENDED | TERMINATED

    model_config = ConfigDict(extra="forbid", frozen=True)

