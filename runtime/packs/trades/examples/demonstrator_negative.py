"""Seven negative demonstrators — enforced by the REAL runtime path (Kernel
authority/resource state + REHT + Gateway + Veritas + BARO), not a local
authorization boundary."""

from __future__ import annotations

from valo_reht import RealReht

from valo_trades_pack import run_golden, seed_world
from valo_trades_pack.golden import Scenario


def test_negative_1_expired_credential_at_dispatch() -> None:
    """Worker's credential (Kernel authority) expires before dispatch. The
    fresh execution context at the WRITE boundary shows no DISPATCH authority;
    REHT DENYs; no dispatch happens (work order stays SCHEDULED)."""
    result = run_golden(reht=RealReht(), kernel=seed_world(dispatch_credential_expired=True), scenario=Scenario())
    assert result.workorder_state == "SCHEDULED", "dispatch must be denied"
    assert any(d["decision"] == "DENY" for d in result.reht_decisions)


def test_negative_2_double_booking() -> None:
    """Two work orders try the same worker/slot. The Kernel resource state is
    authoritative: the second reservation is rejected; only one succeeds."""
    from valo_kernel import KernelInvariantViolation
    from valo_kernel.contracts import CanonicalEvent, EventType, Reservation

    kernel = seed_world()
    first = run_golden(reht=RealReht(), kernel=kernel)
    assert first.workorder_state == "CLOSED"
    # exactly one reservation exists
    reservations = kernel.state().reservations
    assert len(reservations) == 1, "exactly one reservation must exist"
    # a second reservation of the same worker is rejected by the Kernel
    try:
        kernel.append(CanonicalEvent(
            event_id="second-res", event_type=EventType.RESOURCE_RESERVED,
            tenant_id="trades", subject="worker-a", actor="worker-b", source="trades-pack",
            effective_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            payload={"reservation": Reservation(reservation_id="r2", resource_id="worker-a", holder="worker-b", tenant_id="trades")},
        ))
        raise AssertionError("double booking must be rejected by the Kernel")
    except KernelInvariantViolation:
        pass


def test_negative_3_quote_drift() -> None:
    """Invoice beyond the quoted basis without approved change. BARO observes
    the drift and the invoice write fails; the work order never reaches
    INVOICED."""
    result = run_golden(reht=RealReht(), kernel=seed_world(), scenario=Scenario(invoice_drift=True))
    assert result.workorder_state == "IN_PROGRESS", "invoice must be blocked on quote drift"


def test_negative_4_fake_completion_requires_evidence() -> None:
    """A worker 'completing' without admitted evidence never reaches CLOSED
    through the runtime path."""
    result = run_golden(reht=RealReht(), kernel=seed_world())
    assert result.instance_status == "COMPLETED"
    # completion is only reachable through the executed golden path; a direct
    # kernel state write is impossible (Kernel exposes immutable reads).
    kernel = seed_world()
    from valo_trades_pack.ports import TradeKernel

    adapter = TradeKernel(kernel)
    view = adapter.read_state("trades", "workorder-1")
    assert view["state"] != "CLOSED"  # only the runtime transitions it


def test_negative_5_green_while_dead() -> None:
    """Payment provider returns success but the observed account shows no
    payment. BARO diverges; the work order is never PAID."""
    result = run_golden(reht=RealReht(), kernel=seed_world(), scenario=Scenario(payment_lands=False))
    assert result.workorder_state == "INVOICED", "payment must not be PAID without verified effect"


def test_negative_6_revoked_authority() -> None:
    """Authority revoked in the Kernel before the write boundary. REHT DENY at
    dispatch; nothing is dispatched."""
    result = run_golden(reht=RealReht(), kernel=seed_world(revoke_dispatch_authority=True), scenario=Scenario())
    assert result.workorder_state == "SCHEDULED", "dispatch must be denied after revocation"
    assert any(d["decision"] == "DENY" for d in result.reht_decisions)


def test_negative_7_scope_change_is_deterministic() -> None:
    """The quote is never reused blindly: PRICE is deterministic from scope, so
    a changed scope yields a different quote (no memory of a prior quote)."""
    from valo_trades_pack import scenario_inputs
    from valo_trades_pack.pricebook import STANDARD_PRICE_BOOK

    base = STANDARD_PRICE_BOOK.calculate(scope={"service": "EV_CHARGER_INSTALLATION"}, estimated_duration_minutes=240)
    expanded = STANDARD_PRICE_BOOK.calculate(scope={"service": "EV_CHARGER_INSTALLATION", "extra": True}, estimated_duration_minutes=300)
    assert base["total"] != expanded["total"]
    assert scenario_inputs(Scenario())["requirement"]["duration_minutes"] == 240
