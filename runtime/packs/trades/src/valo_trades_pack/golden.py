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

from .functions import build_trades_registry
from .ports import TradeBaro, TradeGateway, TradeKernel, TradeVeritas
from .world import seed_world

# (call_id, function_id, input source). Source is either a graph input name or
# the id of an upstream FunctionCall whose output feeds this input (typed
# composition proven by the Function algebra).
GOLDEN_PATH: list[tuple[str, str, dict[str, str]]] = [
    ("s0", "valo.identity.verify_identity", {"candidate": "identity"}),
    ("s1", "valo.trades.register_workorder", {"registration": "registration"}),
    ("s2", "valo.trades.classify_service", {"request": "request"}),
    ("s3", "valo.trades.check_site_requirements", {"site": "site"}),
    ("s4", "valo.finance.price", {"scope": "scope"}),
    ("s5", "valo.trades.generate_quote", {"request": "request"}),
    ("s6", "valo.decision.approve", {"approval": "approval"}),
    ("s7", "valo.trades.notify", {"notification": "notification"}),
    ("s8", "valo.trades.receive_acceptance", {"quote": "quote"}),
    ("s9", "valo.resource.match", {"requirement": "requirement"}),
    ("s10", "valo.trades.select_worker", {"candidates": "s9"}),
    ("s11", "valo.trades.verify_credential", {"worker": "s10"}),
    ("s12", "valo.trades.schedule", {"requirement": "schedule_requirement"}),
    ("s13", "valo.trades.reserve", {"resource": "s10"}),
    ("s14", "valo.trades.dispatch", {"reservation": "s13"}),
    ("s15", "valo.trades.execute_work", {"decision": "s14"}),
    ("s16", "valo.evidence.verify", {"evidence_in": "evidence"}),
    ("s17", "valo.trades.verify_job_completion", {"evidence": "s16"}),
    ("s18", "valo.trades.issue_invoice", {"completion": "s17"}),
    ("s19", "valo.trades.notify", {"notification": "notification"}),
    ("s20", "valo.trades.receive_payment", {"obligation": "obligation"}),
    ("s21", "valo.trades.reconcile_payment", {"payment": "s20"}),
    ("s22", "valo.trades.verify_postconditions", {"work_order": "work_order"}),
    ("s23", "valo.trades.close_work_order", {"verified": "s22"}),
]

CORE_REUSE_CHECK = [
    "valo.identity.verify_identity",
    "valo.evidence.verify",
    "valo.resource.match",
    "valo.finance.price",
    "valo.decision.approve",
]


@dataclass
class Scenario:
    applicant: dict[str, Any] = field(default_factory=lambda: {"name": "Anna"})
    request_text: str = "Jeg vil ha installert hjemmelader i garasjen."
    site_address: str = "Exampleveien 1"
    accepted: bool = True
    evidence_status: str = "ADMITTED"
    payment_lands: bool = True
    invoice_drift: bool = False
    dispatch_credential_expired: bool = False
    worker_b_qualified: bool = False
    revoked_dispatch_authority: bool = False


def build_golden_graph(registry) -> FunctionGraph:
    calls = []
    inputs: dict[str, str] = {}
    input_types = {
        "identity": "IdentityCandidate",
        "registration": "Registration",
        "request": "Request",
        "site": "Site",
        "scope": "PriceScope",
        "approval": "ApprovalRequest",
        "notification": "Notification",
        "quote": "Quote",
        "requirement": "ResourceRequirement",
        "schedule_requirement": "ScheduleRequirement",
        "evidence": "Evidence",
        "obligation": "PaymentObligation",
        "work_order": "WorkOrder",
    }
    for call_id, function_id, bindings in GOLDEN_PATH:
        definition = registry.resolve(function_id, "1.0.0")
        for graph_name in bindings.values():
            if not (graph_name.startswith("s") and graph_name[1:].isdigit()):
                inputs.setdefault(graph_name, input_types[graph_name])
        out_name = "out_final" if call_id == GOLDEN_PATH[-1][0] else f"out_{call_id}"
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
        graph_id="graph.ev_charger_job", version="2",
        inputs=inputs,
        outputs={"out_final": terminal_definition.output_type.type},
        nodes=calls,
        edges=edges,
        entry_nodes=[calls[0].id],
        terminal_nodes=[calls[-1].id],
    )


def compile_golden(registry) -> Any:
    return compile_function_graph(build_golden_graph(registry), registry.snapshot())


def scenario_inputs(scenario: Scenario) -> dict[str, Any]:
    return {
        "identity": {"name": scenario.applicant.get("name")},
        "registration": {"id": "wo-reg-1"},
        "request": {"description": scenario.request_text},
        "site": {"address": scenario.site_address},
        "scope": {"service": "EV_CHARGER_INSTALLATION"},
        "approval": {"id": "approval-1"},
        "notification": {"recipient": "customer-1", "message": "status update"},
        "quote": {"id": "quote-1", "total": "16500.00"},
        "requirement": {"service": "EV_CHARGER_INSTALLATION", "duration_minutes": 240},
        "schedule_requirement": {"slot": "slot-1"},
        "evidence": [{"type": "installation_completed", "status": scenario.evidence_status, "purpose": "EV_CHARGER_INSTALLATION"}],
        "obligation": {"invoice_id": "inv-1", "amount": "16500.00"},
        "work_order": {"id": "workorder-1"},
    }


@dataclass
class GoldenPathResult:
    final_state: str
    instance_status: str
    kernel_events: int
    gateway_executions: int
    reht_decisions: list[dict[str, Any]]
    workorder_state: str | None
    trace: list[dict[str, Any]] = field(default_factory=list)
    economics: dict[str, Any] = field(default_factory=dict)


def run_golden(
    kernel=None,
    scenario: Scenario | None = None,
    *,
    reht=None,
    shadow: bool = False,
    revoked_capability: str | None = None,
) -> GoldenPathResult:
    """Run the SAME compiled EV_CHARGER_JOB graph through the Workflow ISA
    Runtime, against Kernel-owned state and the REHT/RACS/Gateway/Veritas/BARO
    ports. The pack owns neither authorization nor a parallel state machine:
    the REHT port must be injected from outside the pack (valo-reht
    until the canonical REHT is packaged as a dependency)."""
    if reht is None:
        raise ValueError(
            "no REHT port injected: the pack does not own authorization; "
            "pass the reference/canonical REHT from outside the pack"
        )
    scenario = scenario or Scenario()
    kernel = kernel or seed_world(
        dispatch_credential_expired=scenario.dispatch_credential_expired,
        revoke_dispatch_authority=scenario.revoked_dispatch_authority,
    )
    registry = build_trades_registry()
    graph = build_golden_graph(registry)
    compiled = compile_function_graph(graph, registry.snapshot())

    trade_kernel = TradeKernel(kernel, shadow=shadow)
    gateway = TradeGateway(shadow=shadow)
    veritas = TradeVeritas(payment_lands=scenario.payment_lands, invoice_drift=scenario.invoice_drift)
    backend = ReferenceBackend()
    engine = RuntimeEngine(
        trade_kernel, reht, gateway, veritas, TradeBaro(),
        backend=backend, tenant_id="trades",
    )

    instance = engine.start(compiled.workflow_graph, scenario_inputs(scenario))

    while instance.status == WorkflowStatus.DEFERRED:
        deferred = [nid for nid, status in instance.node_statuses.items() if status == "DEFERRED"]
        if not deferred:
            break
        instance = engine.resume(instance, {"accepted": True})

    workorder_state = None
    try:
        workorder_state = kernel.state().entities["workorder-1"].state
    except KeyError:
        pass

    economics = {
        "functions": len(GOLDEN_PATH),
        "gateway_executions": len(gateway.executions),
        "proposed_executions": len(gateway.proposed),
        "proposed_kernel_events": len(trade_kernel.proposed_events),
        "kernel_events": kernel.sequence(),
        "final_state": workorder_state,
    }
    return GoldenPathResult(
        final_state=workorder_state,
        instance_status=instance.status.value,
        kernel_events=kernel.sequence(),
        gateway_executions=len(gateway.executions),
        reht_decisions=[{"decision": d.decision, "reason": d.reason} for d in reht.decisions],
        workorder_state=workorder_state,
        economics=economics,
    )
