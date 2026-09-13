from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from ..contracts.common import NodeStatus, WorkflowStatus, utcnow
from ..contracts.graph import WorkflowGraph


class WorkflowInstance(BaseModel):
    """Mutable runtime state for one graph execution. Persisted via the
    RuntimeBackend so the workflow can be resumed."""

    instance_id: str = Field(default_factory=lambda: str(uuid4()))
    graph: WorkflowGraph
    status: WorkflowStatus = WorkflowStatus.PENDING
    input_values: dict[str, Any] = Field(default_factory=dict)
    node_statuses: dict[str, NodeStatus] = Field(default_factory=dict)
    attempts: dict[str, int] = Field(default_factory=dict)
    outputs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    errors: dict[str, str] = Field(default_factory=dict)
    correlation_id: str | None = None
    parent_instance_id: str | None = None
    call_stack: list[str] = Field(default_factory=list)
    halt_reason: str | None = None
    deferred_until_input: bool = False
    completion_order: list[str] = Field(default_factory=list)
    deferred_inputs: dict[str, dict[str, Any]] = Field(default_factory=dict)
    compensating: bool = False
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)

    model_config = ConfigDict(extra="forbid")

    def init_node_states(self) -> None:
        for node in self.graph.nodes:
            self.node_statuses.setdefault(node.id, NodeStatus.PENDING)
            self.attempts.setdefault(node.id, 0)

    def touch(self) -> None:
        self.updated_at = utcnow()

    def serialize(self) -> dict[str, Any]:
        return self.model_dump(mode="json")

    @classmethod
    def deserialize(cls, data: dict[str, Any]) -> WorkflowInstance:
        graph = WorkflowGraph.model_validate(data["graph"])
        return cls.model_validate({**data, "graph": graph})
