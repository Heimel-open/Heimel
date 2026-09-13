from __future__ import annotations

from ..contracts.graph import FunctionGraph
from ..types.strength import can_consume
from .errors import TypecheckError
from .resolver import ResolvedCall


def check_call_bindings(fgraph: FunctionGraph, resolved: dict[str, ResolvedCall]) -> None:
    """Typed composition (Function algebra) over input bindings. A Function's
    primary input is bound to either a graph input or an upstream Function's
    output; the bound source type must be consumable by the input type.

      A: X -> Verified<Y>, B: Verified<Y> -> Z, bind B.input <- A.output
         => valid
      A: X -> Raw<Y>,     B: Verified<Y> -> Z, bind B.input <- A.output
         => INVALID (no implicit promotion)
    """
    node_map = fgraph.node_map()
    for call in fgraph.nodes:
        definition = resolved[call.id].definition
        primary = definition.input_type

        # Validate no extraneous input bindings
        unknown_inputs = set(call.input_bindings) - {primary.name}
        if unknown_inputs:
            raise TypecheckError(
                f"call {call.id}: unknown input binding(s) {sorted(unknown_inputs)} for {definition.identity} "
                f"(expected: {primary.name})"
            )

        # Validate no extraneous output bindings
        unknown_outputs = set(call.output_bindings) - {definition.output_type.name}
        if unknown_outputs:
            raise TypecheckError(
                f"call {call.id}: unknown output binding(s) {sorted(unknown_outputs)} for {definition.identity} "
                f"(expected: {definition.output_type.name})"
            )

        source = call.input_bindings.get(primary.name, primary.name)
        if source in fgraph.inputs:
            graph_type = fgraph.inputs[source]
            if not can_consume(graph_type, primary.type):
                raise TypecheckError(
                    f"call {call.id}: graph input {source}:{graph_type} cannot satisfy "
                    f"{primary.type} ({call.function_ref.identity})"
                )
        elif source in node_map:
            upstream = resolved[source].definition
            if not can_consume(upstream.output_type.type, primary.type):
                raise TypecheckError(
                    f"call {call.id}: {upstream.identity} output {upstream.output_type.type} "
                    f"cannot satisfy {primary.type} ({call.function_ref.identity}) — no implicit promotion"
                )
        else:
            raise TypecheckError(
                f"call {call.id}: input {primary.name} bound to unknown source {source}"
            )


def check_graph_inputs(fgraph: FunctionGraph, resolved: dict[str, ResolvedCall]) -> None:
    """Entry Functions' inputs must be satisfiable by graph inputs."""
    node_map = fgraph.node_map()
    for call_id in fgraph.entry_nodes:
        call = node_map[call_id]
        definition = resolved[call_id].definition
        source = call.input_bindings.get(definition.input_type.name, definition.input_type.name)
        if source not in fgraph.inputs:
            raise TypecheckError(
                f"entry {call_id}: {definition.identity} input {definition.input_type.name} "
                f"bound to {source} which is not a graph input; graph inputs: {sorted(fgraph.inputs)}"
            )


def check_graph_outputs(fgraph: FunctionGraph, resolved: dict[str, ResolvedCall]) -> None:
    node_map = fgraph.node_map()
    terminal_calls = [(node_map[nid], resolved[nid]) for nid in fgraph.terminal_nodes]
    for name, output_type in fgraph.outputs.items():
        produced = False
        for call, rc in terminal_calls:
            produced_type = rc.definition.output_type
            graph_name = call.output_bindings.get(produced_type.name, produced_type.name)
            if graph_name == name and can_consume(produced_type.type, output_type):
                produced = True
                break
        if not produced:
            raise TypecheckError(f"graph output {name}:{output_type} not produced by any terminal function")
