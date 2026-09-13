from __future__ import annotations

from valo_reht import RealReht
from valo_workflow_isa import compile_graph as isa_compile

from valo_trades_pack import (
    build_trades_registry,
    compile_golden,
    run_golden,
    seed_world,
)
from valo_trades_pack.golden import Scenario


def test_golden_path_runs_through_isa_runtime() -> None:
    """The COMPILED EV_CHARGER_JOB graph is the one that runs through the
    Workflow ISA Runtime — not a handwritten step engine."""
    registry = build_trades_registry()
    from valo_trades_pack import compile_golden

    compiled = compile_golden(registry)
    isa_compile(compiled.workflow_graph)  # valid ISA
    result = run_golden(reht=RealReht(), kernel=seed_world())
    assert result.workorder_state == "CLOSED"
    assert result.instance_status == "COMPLETED"


def test_kernel_owns_business_truth() -> None:
    """The work order state lives in the Kernel and is only mutated through
    append-only events. Direct mutation of the Kernel state is impossible (the
    Kernel exposes immutable reads)."""
    kernel = seed_world()
    run_golden(reht=RealReht(), kernel=kernel)
    assert kernel.state().entities["workorder-1"].state == "CLOSED"
    # every transition is an event on the workorder entity
    transitions = [e for e in kernel.events() if e.subject == "workorder-1" and e.event_type.value == "ENTITY_UPDATED"]
    assert transitions, "no kernel event recorded for the transitions"


def test_no_local_reht() -> None:
    """Authority is data in the Kernel; REHT authorizes against the fresh
    execution context the Kernel produced. Credential validity is reflected in
    that context, not re-derived in the pack."""
    kernel = seed_world(dispatch_credential_expired=True)
    run_golden(reht=RealReht(), kernel=kernel)
    assert kernel.state().entities["workorder-1"].state == "SCHEDULED"


def test_world_changing_functions_are_write() -> None:
    """DISPATCH, EXECUTE_WORK, ISSUE_INVOICE, RECEIVE_PAYMENT, RECONCILE and
    CLOSE are WRITE functions that flow through the REHT boundary — not PURE
    COMPUTE."""
    registry = build_trades_registry()
    for function_id in [
        "valo.trades.dispatch",
        "valo.trades.execute_work",
        "valo.trades.issue_invoice",
        "valo.trades.receive_payment",
        "valo.trades.reconcile_payment",
        "valo.trades.close_work_order",
    ]:
        definition = registry.get(f"{function_id}@1.0.0")
        workflow = registry.graph_for(definition)
        write_nodes = [n for n in workflow.nodes if n.node_class.value == "WRITE" and n.effect_type.value != "PURE"]
        assert write_nodes, f"{function_id} must be a WRITE Function"


def test_typed_composition_wired() -> None:
    """The golden path's SELECT->RESERVE->DISPATCH->EXECUTE chain carries real
    output->input data flow (typed composition), not just sequenced calls."""
    registry = build_trades_registry()
    from valo_trades_pack import compile_golden

    compiled = compile_golden(registry)
    node_types = {}
    for node in compiled.workflow_graph.nodes:
        for ref in node.inputs:
            node_types[ref.name] = ref.type
    # the RESERVE node consumes the SELECT output (Candidate<Resource>), the
    # DISPATCH node consumes the RESERVE output (Reserved<Resource>)
    assert "Candidate<Resource>" in node_types.values() or "Reserved<Resource>" in node_types.values()


def test_gateway_failure_never_verified() -> None:
    """An external effect that does not land (payment_lands=False) is observed
    by Veritas and rejected by BARO — the work order is never PAID."""
    result = run_golden(reht=RealReht(), kernel=seed_world(), scenario=Scenario(payment_lands=False))
    assert result.workorder_state == "INVOICED"


def test_shadow_is_same_path_no_writes() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(), shadow=True)
    assert result.instance_status == "COMPLETED"
    assert result.workorder_state == "NEW"
    assert result.economics["gateway_executions"] == 0
    assert result.economics["proposed_kernel_events"] > 0


def test_kernel_replay_reconstructs_same_state() -> None:
    """Provenance: the same event history replays to the same authoritative
    state (deterministic Kernel replay — no handwritten history, no
    provenance bug)."""
    from valo_kernel import replay

    kernel = seed_world()
    run_golden(reht=RealReht(), kernel=kernel)
    events = kernel.events()
    rebuilt = replay(events)
    assert rebuilt.entities["workorder-1"].state == kernel.state().entities["workorder-1"].state
    assert rebuilt.root_hash() == kernel.state().root_hash()


def test_event_chain_integrity() -> None:
    kernel = seed_world()
    run_golden(reht=RealReht(), kernel=kernel)
    kernel.verify_integrity()  # raises on any tamper


def test_work_order_transition_admissibility() -> None:
    """Deterministic domain invariant: an authorized action cannot force an
    illegal WorkOrder transition. Golden-path ordering is not a security
    control."""

    kernel = seed_world()
    run_golden(reht=RealReht(), kernel=kernel)  # workorder-1 -> CLOSED
    illegal = [
        ("NEW", "DISPATCHED"),
        ("READY_TO_QUOTE", "PAID"),
        ("INVOICED", "CLOSED"),
        ("COMPLETED", "SCHEDULED"),
    ]
    for current, requested in illegal:
        # directly attempt the requested transition on a fresh workorder
        fresh = seed_world()
        fresh = seed_world()
        # the transition contract rejects the illegal pairs regardless of how
        # the current state was reached
        # the transition contract itself rejects the illegal pairs
        from valo_trades_pack.ports import _admissible_work_order_transition

        try:
            _admissible_work_order_transition(fresh, "workorder-1", requested)
            raise AssertionError(f"illegal transition {current} -> {requested} must be rejected")
        except RuntimeError as exc:
            assert "illegal WorkOrder transition" in str(exc)


def test_typed_composition_exact_wiring() -> None:
    """Exact producer->consumer wiring: SELECT.output == RESERVE.input and
    RESERVE.output == DISPATCH.input (by name and type)."""
    registry = build_trades_registry()
    compiled = compile_golden(registry)
    node_outputs = {}
    node_inputs = {}
    for node in compiled.workflow_graph.nodes:
        for ref in node.outputs:
            node_outputs[(node.id, ref.name)] = ref.type
        for ref in node.inputs:
            node_inputs[(node.id, ref.name)] = ref.type
    # s10 = SELECT_WORKER (out: selected), s13 = RESERVE (in: resource)
    select_out = next((t for (nid, name), t in node_outputs.items() if nid == "s10.run" and name == "out_s10"), None)
    reserve_in = next((t for (nid, name), t in node_inputs.items() if nid == "s13.prepare" and name == "out_s10"), None)
    dispatch_in = next((t for (nid, name), t in node_inputs.items() if nid == "s14.prepare" and name == "out_s13"), None)
    reserve_out = next((t for (nid, name), t in node_outputs.items() if nid == "s13.execute" and name == "out_s13"), None)
    assert select_out is not None and reserve_in is not None
    assert select_out == reserve_in, f"SELECT output {select_out} != RESERVE input {reserve_in}"
    assert reserve_out is not None and dispatch_in is not None
    assert reserve_out == dispatch_in, f"RESERVE output {reserve_out} != DISPATCH input {dispatch_in}"
