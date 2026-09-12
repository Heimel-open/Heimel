from __future__ import annotations

from valo_function_fabric.contracts import (
    FunctionCall,
    FunctionEdge,
    FunctionGraph,
    FunctionRef,
)


def call(node_id: str, function_id: str, version: str = "1.0.0", input_bindings: dict | None = None, output_bindings: dict | None = None) -> FunctionCall:
    return FunctionCall(
        id=node_id,
        function_ref=FunctionRef(function_id=function_id, version=version),
        input_bindings=input_bindings or {},
        output_bindings=output_bindings or {},
    )


def graph(
    graph_id: str,
    calls: list[FunctionCall],
    edges: list[FunctionEdge] | None = None,
    inputs: dict | None = None,
    outputs: dict | None = None,
    entry_nodes: list[str] | None = None,
    terminal_nodes: list[str] | None = None,
) -> FunctionGraph:
    return FunctionGraph(
        graph_id=graph_id,
        version="1",
        inputs=inputs or {},
        outputs=outputs or {},
        nodes=calls,
        edges=edges or [],
        entry_nodes=entry_nodes if entry_nodes is not None else [calls[0].id],
        terminal_nodes=terminal_nodes if terminal_nodes is not None else [calls[-1].id],
    )

