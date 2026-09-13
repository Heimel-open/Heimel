from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..contracts.events import WorkflowEvent, WorkflowEventType
from ..contracts.graph import WorkflowGraph, WorkflowNode
from ..ports.boundaries import (
    BaroPort,
    GatewayPort,
    KernelPort,
    RehtPort,
    VeritasPort,
)
from .instance import WorkflowInstance


class HandlerContext:
    """Everything a node handler may touch. Ports are the only boundary to the
    outside world; the workflow never holds a mutable WorldState."""

    def __init__(
        self,
        *,
        instance: WorkflowInstance,
        node: WorkflowNode,
        graph: WorkflowGraph,
        kernel: KernelPort,
        reht: RehtPort,
        gateway: GatewayPort,
        veritas: VeritasPort,
        baro: BaroPort,
        emit: Callable[[WorkflowEvent], None],
        resolve_scope: Callable[[WorkflowInstance, str], dict[str, Any]],
        run_child: Callable[..., dict[str, Any]] | None = None,
    ) -> None:
        self.instance = instance
        self.node = node
        self.graph = graph
        self.kernel = kernel
        self.reht = reht
        self.gateway = gateway
        self.veritas = veritas
        self.baro = baro
        self._emit = emit
        self.resolve_scope = resolve_scope
        self.run_child = run_child

    @property
    def injected(self) -> dict[str, Any] | None:
        return self.instance.deferred_inputs.get(self.node.id)

    @property
    def tenant_id(self) -> str:
        return self.graph.input_schema.get(
            "__tenant", self.instance.input_values.get("__tenant", "default")
        )

    def emit(self, event_type: WorkflowEventType, payload: dict[str, Any] | None = None) -> None:
        self._emit(
            WorkflowEvent(
                event_type=event_type,
                workflow_instance_id=self.instance.instance_id,
                graph_id=self.graph.id,
                graph_version=self.graph.version,
                node_id=self.node.id,
                attempt=self.instance.attempts.get(self.node.id, 1),
                correlation_id=self.instance.correlation_id,
                payload=payload or {},
            )
        )

    def context_hash(self) -> str:
        from ..contracts.common import canonical_digest

        scope = self.resolve_scope(self.instance, self.node.id)
        return canonical_digest(scope)
