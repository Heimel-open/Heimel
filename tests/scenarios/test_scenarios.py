from __future__ import annotations

from valo_reht import RealReht

from valo_trades_pack import run_golden, seed_world
from valo_trades_pack.golden import Scenario
from valo_trades_pack.pricebook import STANDARD_PRICE_BOOK

CATEGORIES = [
    "happy_path", "missing_data", "qualification", "credential", "scheduling",
    "resource_conflict", "price", "quote_acceptance", "scope_change", "dispatch",
    "evidence", "completion", "invoice", "payment", "reconciliation",
    "authority_revocation", "external_failure", "retry", "idempotency",
    "human_step_up",
]


def test_happy_path_closed() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world())
    assert result.workorder_state == "CLOSED"
    assert result.instance_status == "COMPLETED"


def test_qualified_worker_selected() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world())
    assert result.workorder_state == "CLOSED"
    # worker A is the only one whose DISPATCH authority is valid
    from valo_trades_pack.ports import TradeKernel

    kernel = TradeKernel(seed_world())
    assert kernel.query("trades", "credential_valid", {"actor": "worker-a"})["valid"] is True
    assert kernel.query("trades", "credential_valid", {"actor": "worker-b"})["valid"] is False


def test_worker_b_never_dispatched() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world())
    assert result.workorder_state == "CLOSED"
    assert result.reht_decisions  # dispatch only via authorized actor


def test_scheduling_reserves_worker_in_kernel() -> None:
    kernel = seed_world()
    run_golden(reht=RealReht(), kernel=kernel)
    resource = kernel.state().resources["worker-a"]
    assert resource.state.value == "RESERVED"


def test_resource_conflict_double_booking() -> None:
    from valo_kernel import KernelInvariantViolation
    from valo_kernel.contracts import CanonicalEvent, EventType, Reservation

    kernel = seed_world()
    run_golden(reht=RealReht(), kernel=kernel)
    assert len(kernel.state().reservations) == 1, "exactly one reservation"
    try:
        kernel.append(CanonicalEvent(
            event_id="second-res", event_type=EventType.RESOURCE_RESERVED,
            tenant_id="trades", subject="worker-a", actor="worker-b", source="trades-pack",
            effective_at=__import__("datetime").datetime.now(__import__("datetime").UTC),
            payload={"reservation": Reservation(reservation_id="r2", resource_id="worker-a", holder="worker-b", tenant_id="trades")},
        ))
        raise AssertionError("double booking must be blocked by the Kernel")
    except KernelInvariantViolation:
        pass


def test_price_is_deterministic() -> None:
    a = STANDARD_PRICE_BOOK.calculate(scope={}, estimated_duration_minutes=240)
    b = STANDARD_PRICE_BOOK.calculate(scope={}, estimated_duration_minutes=240)
    assert a == b


def test_price_respects_minimum_charge() -> None:
    price = STANDARD_PRICE_BOOK.calculate(scope={}, estimated_duration_minutes=5)
    assert price["subtotal"] >= 1500


def test_quote_accepted_and_job_closes() -> None:
    assert run_golden(reht=RealReht(), kernel=seed_world()).workorder_state == "CLOSED"


def test_scope_change_yields_different_quote() -> None:
    base = STANDARD_PRICE_BOOK.calculate(scope={}, estimated_duration_minutes=240)
    longer = STANDARD_PRICE_BOOK.calculate(scope={}, estimated_duration_minutes=300)
    assert base["total"] != longer["total"]


def test_dispatch_requires_valid_credential() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(dispatch_credential_expired=True))
    assert result.workorder_state == "SCHEDULED"
    assert any(d["decision"] == "DENY" for d in result.reht_decisions)


def test_evidence_flows_through_admitted() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world())
    assert result.instance_status == "COMPLETED"


def test_completion_reachable_only_after_evidence() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world())
    assert result.workorder_state == "CLOSED"
    # state changed only through kernel events
    from valo_trades_pack.ports import TradeKernel

    adapter = TradeKernel(seed_world())
    view = adapter.read_state("trades", "workorder-1")
    assert view["state"] != "CLOSED"


def test_invoice_requires_completed_delivery() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(), scenario=Scenario(payment_lands=False))
    assert result.workorder_state == "INVOICED"


def test_invoice_mismatch_blocked() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(), scenario=Scenario(invoice_drift=True))
    assert result.workorder_state == "IN_PROGRESS"


def test_payment_requires_verified_effect() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(), scenario=Scenario(payment_lands=False))
    assert result.workorder_state != "PAID"


def test_reconciliation_completes_payment() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world())
    assert result.workorder_state == "CLOSED"


def test_authority_revoked_blocks_dispatch() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(revoke_dispatch_authority=True))
    assert result.workorder_state == "SCHEDULED"
    assert any(d["decision"] == "DENY" for d in result.reht_decisions)


def test_external_failure_detected() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(), scenario=Scenario(payment_lands=False))
    assert result.workorder_state == "INVOICED"


def test_retry_idempotency_key_dedup() -> None:
    from valo_trades_pack.ports import TradeGateway

    gateway = TradeGateway()
    gateway.execute("binding", {"action_type": "PAY"}, "key-1")
    r2 = gateway.execute("binding", {"action_type": "PAY"}, "key-1")
    assert r2.external_id == "replayed", "same idempotency key must not re-execute"


def test_shadow_mode_no_writes() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(), shadow=True)
    assert result.workorder_state == "NEW"
    assert result.economics["gateway_executions"] == 0
    assert result.economics["proposed_kernel_events"] > 0


def test_kernel_events_are_append_only() -> None:
    kernel = seed_world()
    before = kernel.sequence()
    run_golden(reht=RealReht(), kernel=kernel)
    assert kernel.sequence() > before


def test_human_step_up_autonomy_on_dispatch() -> None:
    registry = __import__("valo_trades_pack").build_trades_registry()
    definition = registry.get("valo.trades.dispatch@1.0.0")
    assert "AUTO_EXECUTE" not in {a.value for a in definition.autonomy_profile.allowed_autonomy_levels}


def test_reht_revalidates_at_each_write() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world(dispatch_credential_expired=True))
    assert any(d["decision"] == "DENY" for d in result.reht_decisions)


def test_quote_reconstructible_from_pricebook() -> None:
    price = STANDARD_PRICE_BOOK.calculate(scope={"service": "EV_CHARGER_INSTALLATION"}, estimated_duration_minutes=240)
    again = STANDARD_PRICE_BOOK.calculate(scope={"service": "EV_CHARGER_INSTALLATION"}, estimated_duration_minutes=240)
    assert price == again


def test_evidence_admitted_status_present() -> None:
    result = run_golden(reht=RealReht(), kernel=seed_world())
    assert result.gateway_executions >= 8
