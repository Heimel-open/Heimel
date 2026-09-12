from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import EdgeType, FailurePolicy
from .node import WorkflowNode


class WorkflowEdge(BaseModel):
    """An explicit edge. All edges must be declared; there is no implicit
    control flow."""

    source: str  # node id
    target: str  # node id
    edge_type: EdgeType = EdgeType.NEXT
    condition: str | None = None  # expression evaluated on the source's output

    model_config = ConfigDict(extra="forbid", frozen=True)


class WorkflowGraph(BaseModel):
    """A compiled-and-validated workflow graph. `entry` and every `terminal_state`
    are node ids; all edges are explicit."""

    id: str
    version: str
    input_schema: dict[str, str] = Field(default_factory=dict)  # name -> type
    output_schema: dict[str, str] = Field(default_factory=dict)
    nodes: list[WorkflowNode] = Field(default_factory=list)
    edges: list[WorkflowEdge] = Field(default_factory=list)
    invariants: list[str] = Field(default_factory=list)
    failure_policy: FailurePolicy = FailurePolicy.FAIL
    entry: str
    terminal_states: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_structure(self) -> WorkflowGraph:
        node_ids = [n.id for n in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise ValueError("duplicate node ids")
        if self.entry not in node_ids:
            raise ValueError("entry must reference an existing node")
        for t in self.terminal_states:
            if t not in node_ids:
                raise ValueError(f"terminal_state {t} must reference an existing node")
        for edge in self.edges:
            if edge.source not in node_ids:
                raise ValueError(f"edge source {edge.source} must reference an existing node")
            if edge.target not in node_ids:
                raise ValueError(f"edge target {edge.target} must reference an existing node")
        return self

    def node_map(self) -> dict[str, WorkflowNode]:
        return {n.id: n for n in self.nodes}
