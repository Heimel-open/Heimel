from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from valo_workflow_isa import compile_graph as isa_compile_graph
from valo_workflow_isa.contracts import (
    TypedRef as IsaTypedRef,
)
from valo_workflow_isa.contracts import (
    WorkflowEdge as IsaWorkflowEdge,
)
from valo_workflow_isa.contracts import (
    WorkflowGraph as IsaWorkflowGraph,
)

from ..contracts.common import canonical_digest
from ..contracts.function import FunctionDefinition
from ..contracts.graph import FunctionGraph
from ..contracts.registry import RegistrySnapshot
from .effects import leaf_effects_within_declared, parent_effects_cover_children
from .errors import CompileError
from .governance import check_governance_monotonicity
from .resolver import ResolvedCall, resolve_calls
from .typecheck import check_call_bindings, check_graph_inputs, check_graph_outputs

COMPILER_VERSION = "1.0.0"


@dataclass(frozen=True)
class CompiledFunction:
    function_graph: FunctionGraph
    workflow_graph: IsaWorkflowGraph
    function_graph_hash: str
    registry_snapshot_hash: str
    compiled_graph_hash: str
    compiler_version: str

    def provenance(self) -> dict[str, str]:
        return {
            "function_graph_hash": self.function_graph_hash,
            "registry_snapshot_hash": self.registry_snapshot_hash,
            "compiled_graph_hash": self.compiled_graph_hash,
            "compiler_version": self.compiler_version,
        }

    def verify_provenance(self, snapshot: RegistrySnapshot | None = None) -> bool:
        """Verify that the compiled function has not been mutated or substituted,
        and optionally that its snapshot seal matches."""
        expected_fg_hash = canonical_digest(self.function_graph.model_dump(mode="json"))
        if self.function_graph_hash != expected_fg_hash:
            return False
        expected_wf_hash = canonical_digest(self.workflow_graph.model_dump(mode="json"))
        if self.compiled_graph_hash != expected_wf_hash:
            return False
        return not (snapshot is not None and self.registry_snapshot_hash != snapshot.hash)


def compile_function_graph(
    fgraph: FunctionGraph,
    snapshot: RegistrySnapshot,
    *,
    parent_definition: FunctionDefinition | None = None,
) -> CompiledFunction:
    """Compile a FunctionGraph into a valid Workflow ISA graph.

    Deterministic: the same FunctionGraph + snapshot + input schema always
    produce the same compiled graph hash. Versions are pinned; the result is
    bound to the immutable registry snapshot."""
    resolved = resolve_calls(fgraph, snapshot)

    check_no_recursive_composition(fgraph)
    check_graph_reachability(fgraph)
    check_call_bindings(fgraph, resolved)
    check_graph_inputs(fgraph, resolved)
    check_graph_outputs(fgraph, resolved)

    if parent_definition is not None:
        children = list(resolved.values())
        parent_effects_cover_children(parent_definition, children)
        check_governance_monotonicity(parent_definition, children)

    assembled = _assemble(fgraph, resolved)

    try:
        isa_compile_graph(assembled)
    except Exception as exc:
        raise CompileError(f"FunctionGraph {fgraph.graph_id} compiles to an invalid Workflow ISA graph: {exc}") from exc

    function_graph_hash = canonical_digest(fgraph.model_dump(mode="json"))
    registry_snapshot_hash = snapshot.hash
    compiled_graph_hash = canonical_digest(assembled.model_dump(mode="json"))

    return CompiledFunction(
        function_graph=fgraph,
        workflow_graph=assembled,
        function_graph_hash=function_graph_hash,
        registry_snapshot_hash=registry_snapshot_hash,
        compiled_graph_hash=compiled_graph_hash,
        compiler_version=COMPILER_VERSION,
    )


def validate_function_definition(
    definition: FunctionDefinition, workflow_graph: IsaWorkflowGraph
) -> None:
    """Validate a leaf Function's authored workflow graph: it must be valid ISA
    and its effects must be within the declared effect set (golden invariant)."""
    try:
        isa_compile_graph(workflow_graph)
    except Exception as exc:
        raise CompileError(f"{definition.identity}: workflow_ref is not valid Workflow ISA: {exc}") from exc
    leaf_effects_within_declared(definition, workflow_graph)
    unknown_jurisdictions = [j.country for j in definition.jurisdiction_constraints if j.country.upper() not in KNOWN_JURISDICTIONS]
    if unknown_jurisdictions:
        raise CompileError(
            f"{definition.identity}: unknown jurisdiction(s) {unknown_jurisdictions}; "
            f"known: {sorted(KNOWN_JURISDICTIONS)}"
        )


KNOWN_JURISDICTIONS = frozenset({"NO", "SE", "DK", "FI", "EU", "DE", "GB", "US"})


def check_no_recursive_composition(fgraph: FunctionGraph) -> None:
    """Recursive FunctionGraph composition without an explicit bound is
    rejected. FunctionGraph edges are control-flow edges; a cycle would make
    the compiled Workflow ISA graph cyclic without a LOOP termination node."""
    def dfs(node_id: str, seen: set[str], stack: list[str]) -> bool:
        if node_id in stack:
            return True
        if node_id in seen:
            return False
        seen.add(node_id)
        stack.append(node_id)
        for edge in fgraph.edges:
            if edge.source == node_id and dfs(edge.target, seen, stack):
                return True
        stack.pop()
        return False

    for node in fgraph.nodes:
        if dfs(node.id, set(), []):
            raise CompileError(
                f"FunctionGraph {fgraph.graph_id}: recursive composition without an explicit bound"
            )


def check_graph_reachability(fgraph: FunctionGraph) -> None:
    """Every FunctionCall in fgraph must be reachable from entry_nodes and
    must be able to reach at least one terminal_node (no orphan/disconnected nodes)."""
    node_ids = {n.id for n in fgraph.nodes}
    adj: dict[str, set[str]] = {nid: set() for nid in node_ids}
    rev_adj: dict[str, set[str]] = {nid: set() for nid in node_ids}
    for edge in fgraph.edges:
        adj[edge.source].add(edge.target)
        rev_adj[edge.target].add(edge.source)

    # Forward reachability from entry_nodes
    reachable_from_entry: set[str] = set()
    queue = list(fgraph.entry_nodes)
    while queue:
        curr = queue.pop(0)
        if curr not in reachable_from_entry:
            reachable_from_entry.add(curr)
            queue.extend(adj[curr] - reachable_from_entry)

    unreachable = node_ids - reachable_from_entry
    if unreachable:
        raise CompileError(
            f"FunctionGraph {fgraph.graph_id}: node(s) {sorted(unreachable)} are unreachable from entry nodes"
        )

    # Backward reachability to terminal_nodes
    can_reach_terminal: set[str] = set()
    queue = list(fgraph.terminal_nodes)
    while queue:
        curr = queue.pop(0)
        if curr not in can_reach_terminal:
            can_reach_terminal.add(curr)
            queue.extend(rev_adj[curr] - can_reach_terminal)

    cannot_reach_term = node_ids - can_reach_terminal
    if cannot_reach_term:
        raise CompileError(
            f"FunctionGraph {fgraph.graph_id}: node(s) {sorted(cannot_reach_term)} cannot reach any terminal node"
        )


def _assemble(fgraph: FunctionGraph, resolved: dict[str, ResolvedCall]) -> IsaWorkflowGraph:
    new_nodes: list[Any] = []
    new_edges: list[Any] = []
    entry_map: dict[str, str] = {}
    terminal_map: dict[str, list[str]] = {}
    nodes_by_id: dict[str, Any] = {}

    # Bound output names per call: a downstream input bound to an upstream call
    # must be wired to that call's produced output name (typed composition).
    call_output_names: dict[str, str] = {}
    for call in fgraph.nodes:
        definition = resolved[call.id].definition
        call_output_names[call.id] = call.output_bindings.get(definition.output_type.name, definition.output_type.name)

    for call in fgraph.nodes:
        rc = resolved[call.id]
        wf = rc.workflow_graph
        prefix = call.id
        for node in wf.nodes:
            is_entry = node.id == wf.entry
            is_terminal = node.id in wf.terminal_states
            renamed = _rename_node(
                node, prefix, call,
                is_entry=is_entry, is_terminal=is_terminal,
                call_output_names=call_output_names,
                graph_input_names=set(fgraph.inputs),
            )
            new_nodes.append(renamed)
            nodes_by_id[renamed.id] = renamed
            if node.id == wf.entry:
                entry_map[call.id] = renamed.id
            if node.id in wf.terminal_states:
                terminal_map.setdefault(call.id, []).append(renamed.id)
        for edge in wf.edges:
            new_edges.append(
                IsaWorkflowEdge(source=f"{prefix}.{edge.source}", target=f"{prefix}.{edge.target}", edge_type=edge.edge_type, condition=edge.condition)
            )

    for edge in fgraph.edges:
        for term in terminal_map.get(edge.source, []):
            new_edges.append(IsaWorkflowEdge(source=term, target=entry_map[edge.target], edge_type=edge.edge_type))

    entry = entry_map[fgraph.entry_nodes[0]]
    terminals: list[str] = []
    for tid in fgraph.terminal_nodes:
        terminals.extend(terminal_map.get(tid, []))
    terminals = _dedupe(terminals)

    input_schema: dict[str, str] = {}
    for name, type_expr in fgraph.inputs.items():
        from ..types.strength import workflow_type

        input_schema[name] = workflow_type(type_expr)
    for ref in nodes_by_id[entry].inputs:
        input_schema.setdefault(ref.name, ref.type)
    output_schema: dict[str, str] = {}
    for node_id in terminals:
        for ref in nodes_by_id[node_id].outputs:
            output_schema[ref.name] = ref.type

    return IsaWorkflowGraph(
        id=fgraph.graph_id,
        version=fgraph.version,
        input_schema=input_schema,
        output_schema=output_schema,
        nodes=new_nodes,
        edges=new_edges,
        entry=entry,
        terminal_states=terminals,
    )


def _rename_node(
    node: Any,
    prefix: str,
    call: Any,
    *,
    is_entry: bool,
    is_terminal: bool,
    call_output_names: dict[str, str] | None = None,
    graph_input_names: set[str] | None = None,
) -> Any:
    new_id = f"{prefix}.{node.id}"
    comp_ref = f"{prefix}.{node.compensation_ref}" if node.compensation_ref else None
    if is_entry:
        inputs = [
            IsaTypedRef(name=_resolve_binding(ref.name, call, call_output_names or {}, graph_input_names or set()), type=ref.type)
            for ref in node.inputs
        ]
    else:
        inputs = [
            IsaTypedRef(name=f"{prefix}.{ref.name}", type=ref.type)
            for ref in node.inputs
        ]
    if is_terminal:
        outputs = [
            IsaTypedRef(name=call.output_bindings.get(ref.name, call.id), type=ref.type)
            for ref in node.outputs
        ]
    else:
        outputs = [
            IsaTypedRef(name=f"{prefix}.{ref.name}", type=ref.type)
            for ref in node.outputs
        ]
    return node.model_copy(update={"id": new_id, "compensation_ref": comp_ref, "inputs": inputs, "outputs": outputs})


def _resolve_binding(input_name: str, call: Any, call_output_names: dict[str, str], graph_input_names: set[str]) -> str:
    """A FunctionCall's input_bindings value is either a graph input name or an
    upstream FunctionCall id. When it references an upstream call (and is not
    also a graph input name), the input is wired to that call's bound output
    name (typed composition)."""
    binding = call.input_bindings.get(input_name, input_name)
    if binding in call_output_names and binding not in graph_input_names:
        return call_output_names[binding]
    return binding


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result

