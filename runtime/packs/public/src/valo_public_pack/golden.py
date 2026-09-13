from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from valo_function_fabric.compiler import compile_function_graph
from valo_function_fabric.contracts import (
    FunctionCall,
    FunctionEdge,
    FunctionGraph,
    FunctionRef,
)
from valo_workflow_isa import ReferenceBackend, RuntimeEngine, WorkflowStatus

from .functions import build_public_registry
from .ports import PublicBaro, PublicGateway, PublicKernel, PublicVeritas
from .world import seed_world

# (call_id, function_id, input bindings: {function_input_name: graph_name | upstream_call_id})
# DecisionContext is assembled by the accumulating control chain
# (s1 -> s3 -> s4 -> s5 -> s8 -> s9 -> s11 -> s12 -> s13) and is the ONLY
# input ISSUE_PUBLIC_DECISION accepts — it cannot run on a bare Case.
GOLDEN_PATH: list[tuple[str, str, dict[str, str]]] = [
    ("s0", "valo.identity.verify_identity", {"candidate": "identity"}),
    ("s1", "valo.public.verify_representation", {"case": "case"}),
    ("s2", "valo.public.register_case", {"application": "application"}),
    ("s3", "valo.public.resolve_purpose", {"context": "s1"}),
    ("s4", "valo.public.resolve_legal_basis", {"context": "s3"}),
    ("s5", "valo.public.resolve_competence", {"context": "s4"}),
    ("s6", "valo.evidence.request", {"request": "evidence_request"}),
    ("s7", "valo.evidence.verify", {"evidence_in": "evidence"}),
    ("s8", "valo.public.establish_case_facts", {"context": "s5"}),
    ("s9", "valo.public.check_eligibility", {"context": "s8"}),
    ("s9b", "valo.public.mark_ready_for_review", {"case": "case"}),
    ("s10", "valo.public.mark_under_review", {"case": "case"}),
    ("s11", "valo.public.check_procedural_requirements", {"context": "s9"}),
    ("s12", "valo.public.check_conflict_of_interest", {"context": "s11"}),
    ("s13", "valo.public.prepare_public_decision", {"context": "s12"}),
    ("s13b", "valo.public.mark_ready_for_decision", {"case": "case"}),
    ("s14", "valo.decision.approve", {"approval": "approval"}),
    ("s15", "valo.public.issue_public_decision", {"context": "s13"}),
    ("s16", "valo.public.notify", {"notification": "notification"}),
    ("s17", "valo.public.create_appeal_right", {"decision": "s15"}),
    ("s18", "valo.public.verify_delivery", {"case": "case"}),
    ("s19", "valo.public.finalize_case", {"case": "case"}),
    ("s20", "valo.public.close_case", {"case": "case"}),
]

INPUT_TYPES = {
    "identity": "IdentityCandidate",
    "case": "Case",
    "application": "Application",
    "evidence_request": "EvidenceRequest",
    "evidence": "Evidence",
    "approval": "ApprovalRequest",
    "notification": "Notification",
}


@dataclass
class Scenario:
    """RAW reality only: no adjudicated 'ok' flags. Legal basis, competence,
    evidence, habilitet, representation and eligibility are DERIVED at the
    decision boundary from these raw facts."""
    applicant_name: str = "Applicant A"
    applicant_age: int = 30
    representation_scope_ok: bool = True
    has_representation: bool = False
    residency_conflicted: bool = False
    legal_basis_active: bool = True
    competence_active: bool = True
    revoke_competence: bool = False
    decision_maker_relationship: str | None = None
    notification_delivered: bool = True
    evidence_stale: bool = False
    purpose_violation: bool = False
    service: str = "PUBLIC_SERVICE_A"


def build_golden_graph(registry) -> FunctionGraph:
    calls = []
    inputs: dict[str, str] = {}
    for call_id, function_id, bindings in GOLDEN_PATH:
        definition = registry.resolve(function_id, "1.0.0")
        for graph_name in bindings.values():
            if not (graph_name.startswith("s") and graph_name[1:].isdigit()):
                inputs.setdefault(graph_name, INPUT_TYPES[graph_name])
        out_name = "out_final" if call_id == GOLDEN_PATH[-1][0] else call_id
        calls.append(
            FunctionCall(
                id=call_id,
                function_ref=FunctionRef(function_id=function_id, version="1.0.0"),
                input_bindings=bindings,
                output_bindings={definition.output_type.name: out_name},
            )
        )
    edges = [FunctionEdge(source=calls[i].id, target=calls[i + 1].id) for i in range(len(calls) - 1)]
    terminal_definition = registry.resolve(GOLDEN_PATH[-1][1], "1.0.0")
    return FunctionGraph(
        graph_id="graph.process_public_application", version="2",
        inputs=inputs,
        outputs={"out_final": terminal_definition.output_type.type},
        nodes=calls,
        edges=edges,
        entry_nodes=[calls[0].id],
        terminal_nodes=[calls[-1].id],
    )


def compile_golden(registry) -> Any:
    return compile_function_graph(build_golden_graph(registry), registry.snapshot())


def _count_by_type(executions: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for record in executions:
        action_type = record.get("action_type", "UNKNOWN")
        counts[action_type] = counts.get(action_type, 0) + 1
    return counts


def scenario_inputs(scenario: Scenario) -> dict[str, Any]:
    return {
        "identity": {"name": scenario.applicant_name},
        # the raw case: facts, raw relations, raw evidence, representation,
        # service. The control Functions flow this raw reality into the
        # DecisionContext; the decision boundary derives eligibility, habilitet,
        # evidence acceptability, representation scope and legal basis from it.
        "case": {
            "id": "case-1",
            "service": scenario.service,
            "age": scenario.applicant_age,
            "residency_fact": "CONFLICTED" if scenario.residency_conflicted else "CONFIRMED",
            "relations": (
                [{"subject": "system-1", "object": "applicant-1", "kind": scenario.decision_maker_relationship}]
                if scenario.decision_maker_relationship else []
            ),
            "evidence": [{
                "type": "residency_document",
                "status": "STALE" if scenario.evidence_stale else "ADMITTED",
                "purpose": "SERVICE_B" if scenario.purpose_violation else scenario.service,
            }],
            "representation": (
                {"representative": "rep-1", "scope": "FULL" if scenario.representation_scope_ok else "LIMITED"}
                if scenario.has_representation else None
            ),
        },
        "application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A", "submitted_before_deadline": True},
        "evidence_request": {"type": "residency_document"},
        "evidence": [{"type": "residency_document", "status": "STALE" if scenario.evidence_stale else "ADMITTED", "purpose": "SERVICE_B" if scenario.purpose_violation else scenario.service}],
        "approval": {"id": "approval-1"},
        "notification": {"recipient": "applicant-1", "message": "decision"},
    }


@dataclass
class GoldenPathResult:
    final_state: str
    instance_status: str
    kernel_events: int
    gateway_executions: int
    reht_decisions: list[dict[str, Any]]
    case_state: str | None
    instance: Any | None = None
    backend: Any | None = None
    economics: dict[str, Any] = field(default_factory=dict)


def run_golden(
    kernel=None,
    scenario: Scenario | None = None,
    *,
    reht=None,
    shadow: bool = False,
) -> GoldenPathResult:
    """Run the SAME compiled PROCESS_PUBLIC_APPLICATION graph through the
    Workflow ISA Runtime, against Kernel-owned state and the REHT/Gateway/
    Veritas/BARO ports. The pack owns neither authorization nor a parallel state
    machine: the REHT port must be injected from outside the pack (a test
    double until the canonical REHT is packaged as a dependency)."""
    if reht is None:
        raise ValueError(
            "no REHT port injected: the pack does not own authorization; "
            "pass the real REHT package (valo-reht) or a test double from outside the pack"
        )
    scenario = scenario or Scenario()
    kernel = kernel or seed_world(
        legal_basis_active=scenario.legal_basis_active,
        competence_active=scenario.competence_active,
        revoke_competence=scenario.revoke_competence,
        residency_conflicted=scenario.residency_conflicted,
        decision_maker_relationship=scenario.decision_maker_relationship,
        evidence_stale=scenario.evidence_stale,
        purpose_violation=scenario.purpose_violation,
        has_representation=scenario.has_representation,
        representation_scope_ok=scenario.representation_scope_ok,
        applicant_age=scenario.applicant_age,
        service=scenario.service,
    )
    registry = build_public_registry()
    graph = build_golden_graph(registry)
    compiled = compile_function_graph(graph, registry.snapshot())

    public_kernel = PublicKernel(kernel, shadow=shadow)
    gateway = PublicGateway(shadow=shadow)
    veritas = PublicVeritas(notification_delivered=scenario.notification_delivered)
    backend = ReferenceBackend()
    engine = RuntimeEngine(
        public_kernel, reht, gateway, veritas, PublicBaro(),
        backend=backend, tenant_id="public",
    )

    instance = engine.start(compiled.workflow_graph, scenario_inputs(scenario))
    while instance.status == WorkflowStatus.DEFERRED:
        deferred = [nid for nid, status in instance.node_statuses.items() if status == "DEFERRED"]
        if not deferred:
            break
        instance = engine.resume(instance, {"accepted": True, "evidence": scenario_inputs(scenario)["evidence"]})

    case_state = None
    try:
        case_state = kernel.state().entities["case-1"].state
    except KeyError:
        pass

    economics = {
        "functions": len(GOLDEN_PATH),
        "gateway_executions": len(gateway.executions),
        "proposed_executions": len(gateway.proposed),
        "proposed_kernel_events": len(public_kernel.proposed_events),
        "kernel_events": kernel.sequence(),
        "final_state": case_state,
        "executions_by_type": _count_by_type(gateway.executions),
    }
    return GoldenPathResult(
        final_state=case_state,
        instance_status=instance.status.value,
        kernel_events=kernel.sequence(),
        gateway_executions=len(gateway.executions),
        reht_decisions=[{"decision": d.decision, "reason": d.reason} for d in reht.decisions],
        case_state=case_state,
        instance=instance,
        backend=backend,
        economics=economics,
    )
