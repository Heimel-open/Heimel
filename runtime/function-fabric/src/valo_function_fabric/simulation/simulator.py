from __future__ import annotations

from dataclasses import dataclass, field

from valo_workflow_isa.contracts import NodeClass

from ..compiler import CompiledFunction, compile_function_graph
from ..contracts.common import RISK_ORDER
from ..contracts.graph import FunctionGraph
from ..contracts.registry import RegistrySnapshot


@dataclass(frozen=True)
class SimulationReport:
    function_graph: FunctionGraph
    compiled: CompiledFunction
    required_evidence: list[str]
    required_authority: list[str]
    required_purpose: list[str]
    expected_writes: list[dict[str, str]]
    expected_postconditions: list[str]
    risk: str
    economic_profile_ref: str | None = None
    notes: list[str] = field(default_factory=list)


def simulate(
    fgraph: FunctionGraph,
    snapshot: RegistrySnapshot,
    registry,
) -> SimulationReport:
    """Deterministic simulation. Produces a full structured report with NO
    real-world write and no external execution."""
    compiled = compile_function_graph(fgraph, snapshot)

    required_evidence: set[str] = set()
    required_authority: set[str] = set()
    required_purpose: set[str] = set()
    expected_writes: list[dict[str, str]] = []
    postconditions: list[str] = []
    max_risk: int = -1
    risk_label: str = "R0_INFORMATIONAL"

    for call in fgraph.nodes:
        definition = registry.get(call.function_ref.identity)
        for req in definition.evidence_requirements:
            required_evidence.update(req.required_types)
        for req in definition.authority_requirements:
            required_authority.add(req.capability)
        for req in definition.purpose_requirements:
            required_purpose.update(req.purpose_types)
        postconditions.extend(p.expression for p in definition.postconditions)
        if RISK_ORDER[definition.risk_class] > max_risk:
            max_risk = RISK_ORDER[definition.risk_class]
            risk_label = definition.risk_class.value
    for node in compiled.workflow_graph.nodes:
        if node.node_class == NodeClass.WRITE:
            expected_writes.append(
                {"function": _owner(node.id), "node": node.id, "effect": node.effect_type.value}
            )

    return SimulationReport(
        function_graph=fgraph,
        compiled=compiled,
        required_evidence=sorted(required_evidence),
        required_authority=sorted(required_authority),
        required_purpose=sorted(required_purpose),
        expected_writes=expected_writes,
        expected_postconditions=postconditions,
        risk=risk_label,
    )


def _owner(node_id: str) -> str:
    return node_id.split(".")[0] if "." in node_id else node_id
