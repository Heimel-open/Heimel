from __future__ import annotations

from hypothesis import given, settings
from hypothesis import strategies as st
from valo_reht import RealReht
from valo_workflow_isa import compile_graph as isa_compile

from valo_trades_pack import run_golden, seed_world
from valo_trades_pack.golden import Scenario


@settings(max_examples=10, deadline=None)
@given(st.booleans())
def test_property_no_dispatch_with_invalid_credential(expired) -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(dispatch_credential_expired=expired))
    if expired:
        assert result.workorder_state != "DISPATCHED"
    else:
        assert result.workorder_state == "CLOSED"


def test_property_no_worker_double_booking() -> None:
    from valo_kernel import KernelInvariantViolation
    from valo_kernel.contracts import CanonicalEvent, EventType, Reservation

    kernel = seed_world()
    run_golden(reht=RealReht(), kernel=kernel)
    assert len(kernel.state().reservations) == 1, "only one reservation may exist"
    # the second execution can never get the ALLOCATE effect: the Kernel
    # rejects the reservation, so no second worker reservation ever lands
    try:
        kernel.append(CanonicalEvent(
            event_id="second-res", event_type=EventType.RESOURCE_RESERVED,
            tenant_id="trades", subject="worker-a", actor="worker-b", source="trades-pack",
            effective_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            payload={"reservation": Reservation(reservation_id="r2", resource_id="worker-a", holder="worker-b", tenant_id="trades")},
        ))
        raise AssertionError("second reservation must be rejected")
    except KernelInvariantViolation:
        pass


def test_property_no_paid_without_verified_payment() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(), scenario=Scenario(payment_lands=False))
    assert result.workorder_state != "PAID"


def test_property_no_invoice_without_completed_delivery() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(), scenario=Scenario(invoice_drift=True))
    assert result.workorder_state != "INVOICED"


def test_property_shadow_never_writes() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(), shadow=True)
    assert result.workorder_state == "NEW"
    assert result.economics["gateway_executions"] == 0


def test_property_compiled_graph_is_valid_isa() -> None:
    from valo_trades_pack import build_trades_registry, compile_golden

    isa_compile(compile_golden(build_trades_registry()).workflow_graph)


def test_property_effectful_functions_are_write() -> None:
    registry = __import__("valo_trades_pack").build_trades_registry()
    for function_id in [
        "valo.trades.dispatch",
        "valo.trades.execute_work",
        "valo.trades.issue_invoice",
        "valo.trades.receive_payment",
        "valo.trades.reconcile_payment",
        "valo.trades.close_work_order",
    ]:
        workflow = registry.graph_for(registry.get(f"{function_id}@1.0.0"))
        assert any(n.node_class.value == "WRITE" and n.effect_type.value != "PURE" for n in workflow.nodes)


def test_property_reht_decisions_match_authority() -> None:
    """REHT's ALLOW/DENY decisions are consistent with the Kernel's authority
    state (no local authority derivation in the pack)."""
    expired = run_golden(reht=RealReht(), kernel=seed_world(dispatch_credential_expired=True))
    healthy = run_golden(reht=RealReht(), kernel=seed_world())
    assert any(d["decision"] == "DENY" for d in expired.reht_decisions)
    assert all(d["decision"] == "ALLOW" for d in healthy.reht_decisions)
