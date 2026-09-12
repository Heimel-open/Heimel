from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import Determinism, EffectType, NodeClass
from .policy import NodePolicies


class TypedRef(BaseModel):
    """A named, typed value flowing between nodes. Types use the wrapper system
    (e.g. 'Verified<Recipient>', 'Candidate<Recipient>')."""

    name: str
    type: str

    model_config = ConfigDict(extra="forbid", frozen=True)

    def __hash__(self) -> int:
        return hash((self.name, self.type))


class WorkflowNode(BaseModel):
    """A single typed node in a WorkflowGraph. Frozen contract; `extra=forbid`."""

    id: str
    opcode: str  # ControlOpcode or PrimitiveOpcode value; validated by the compiler
    node_class: NodeClass
    inputs: list[TypedRef] = Field(default_factory=list)
    outputs: list[TypedRef] = Field(default_factory=list)
    preconditions: list[str] = Field(default_factory=list)
    postconditions: list[str] = Field(default_factory=list)
    timeout: float | None = None  # seconds
    policies: NodePolicies = Field(default_factory=NodePolicies)
    effect_type: EffectType = EffectType.PURE
    determinism: Determinism = Determinism.DETERMINISTIC
    compensation_ref: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_node(self) -> WorkflowNode:
        if self.node_class == NodeClass.WRITE and self.effect_type == EffectType.PURE:
            raise ValueError("WRITE nodes must declare a non-PURE effect")
        if self.node_class == NodeClass.COMPUTE and self.determinism == Determinism.PROBABILISTIC:
            # probabilistic classification is allowed on DECIDE; keep rule explicit below
            pass
        if self.node_class == NodeClass.WRITE and self.determinism == Determinism.PROBABILISTIC:
            raise ValueError("a probabilistic node can never be a WRITE")
        if self.compensation_ref is not None and self.compensation_ref == self.id:
            raise ValueError("compensation_ref cannot point to the node itself")
        return self
