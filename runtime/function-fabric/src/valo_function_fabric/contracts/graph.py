from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FunctionRef(BaseModel):
    """A pinned reference to a registered Function: id + version."""

    function_id: str
    version: str

    model_config = ConfigDict(extra="forbid", frozen=True)

    @property
    def identity(self) -> str:
        return f"{self.function_id}@{self.version}"


class FunctionCall(BaseModel):
    """A node in a FunctionGraph referencing a registered Function."""

    id: str
    function_ref: FunctionRef
    input_bindings: dict[str, str] = Field(default_factory=dict)  # function input name -> graph value
    output_bindings: dict[str, str] = Field(default_factory=dict)  # graph value <- function output name
    optional: bool = False

    model_config = ConfigDict(extra="forbid", frozen=True)


class FunctionEdge(BaseModel):
    source: str  # FunctionCall id
    target: str  # FunctionCall id
    edge_type: str = "NEXT"  # NEXT | TRUE | FALSE | ERROR | COMPENSATE

    model_config = ConfigDict(extra="forbid", frozen=True)


class FunctionGraph(BaseModel):
    graph_id: str
    version: str

    inputs: dict[str, str] = Field(default_factory=dict)  # name -> type
    outputs: dict[str, str] = Field(default_factory=dict)  # name -> type

    nodes: list[FunctionCall] = Field(default_factory=list)
    edges: list[FunctionEdge] = Field(default_factory=list)

    invariants: list[str] = Field(default_factory=list)

    entry_nodes: list[str] = Field(default_factory=list)
    terminal_nodes: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid", frozen=True)

    @model_validator(mode="after")
    def validate_structure(self) -> FunctionGraph:
        ids = [n.id for n in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate FunctionCall ids")
        if not self.entry_nodes:
            raise ValueError("entry_nodes is required")
        if not self.terminal_nodes:
            raise ValueError("terminal_nodes is required")
        for node_id in self.entry_nodes + self.terminal_nodes:
            if node_id not in ids:
                raise ValueError(f"node {node_id} must reference an existing FunctionCall")
        for edge in self.edges:
            if edge.source not in ids or edge.target not in ids:
                raise ValueError("edge must reference existing FunctionCalls")
        return self

    def node_map(self) -> dict[str, FunctionCall]:
        return {n.id: n for n in self.nodes}
