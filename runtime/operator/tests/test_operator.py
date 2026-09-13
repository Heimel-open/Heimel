from __future__ import annotations

import inspect

import pytest
from valo_reht import RealReht

from valo_operator import act, kernel_views, operator_snapshot


def _public_parts(legal_basis_active=True):
    from valo_public_pack import build_public_registry, seed_world
    from valo_public_pack.ports import PublicBaro, PublicGateway, PublicKernel, PublicVeritas

    kernel = seed_world(legal_basis_active=legal_basis_active)
    return (
        build_public_registry(),
        PublicKernel(kernel),
        RealReht(),
        PublicGateway(),
        PublicVeritas(),
        PublicBaro(),
        kernel,
    )


def _trades_parts():
    from valo_trades_pack import build_trades_registry, seed_world
    from valo_trades_pack.ports import TradeBaro, TradeGateway, TradeKernel, TradeVeritas

    kernel = seed_world()
    return (
        build_trades_registry(),
        TradeKernel(kernel),
        RealReht(),
        TradeGateway(),
        TradeVeritas(),
        TradeBaro(),
        kernel,
    )


def test_views_are_read_only() -> None:
    _, _, _, _, _, _, kernel = _public_parts()
    before = kernel.sequence()
    views = kernel_views(kernel)
    assert views["event_count"] == before
    assert kernel.sequence() == before, "operator views must never mutate the kernel"


def test_act_rejects_unknown_function_id() -> None:
    registry, adapter, reht, gateway, veritas, baro, _ = _public_parts()
    from valo_function_fabric.registry.store import RegistryError

    with pytest.raises(RegistryError):
        act(registry, adapter, reht, gateway, veritas, baro, function_id="valo.nope.unknown", inputs={})


def test_act_allowed_register() -> None:
    registry, adapter, reht, gateway, veritas, baro, kernel = _public_parts()
    result = act(
        registry, adapter, reht, gateway, veritas, baro,
        function_id="valo.public.register_case",
        inputs={"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}},
    )
    assert result.decision == "ALLOW"
    assert result.permit and result.permit.startswith("permit:")
    assert result.gateway_executions == 1
    assert result.effect_verified is True
    assert kernel.state().entities["case-1"].state == "REGISTERED"


def test_act_denied_without_authority() -> None:
    """REHT DENY: with the ADMIN authority revoked, REGISTER is authorized by
    nobody -> zero Gateway executions, no effect."""
    from valo_kernel.contracts import CanonicalEvent, EventType, utcnow

    registry, adapter, reht, gateway, veritas, baro, kernel = _public_parts()
    kernel.append(CanonicalEvent(
        event_id="revoke-admin", event_type=EventType.AUTHORITY_REVOKED,
        tenant_id="public", subject="system-1", source="kernel", effective_at=utcnow(),
        payload={"authority_id": "auth-system-ADMIN", "revocation_ref": "rev-admin"},
    ))
    result = act(
        registry, adapter, reht, gateway, veritas, baro,
        function_id="valo.public.register_case",
        inputs={"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}},
    )
    assert result.decision == "DENY"
    assert result.gateway_executions == 0
    assert result.effect_verified is False
    assert kernel.state().entities["case-1"].state == "RECEIVED"


def test_effect_comes_from_registered_definition() -> None:
    """A MOVE_MONEY Function cannot be downgraded to WRITE_INTERNAL: the effect
    comes from the registered Function contract, and the operator API exposes
    no effect override."""
    registry, *_ = _public_parts()
    pay_workflow = registry.graph_for(registry.get("valo.finance.pay@1.0.0"))
    effects = {n.effect_type.value for n in pay_workflow.nodes}
    assert effects == {"MOVE_MONEY"}
    signature = inspect.signature(act)
    for param in ("effect_type", "risk", "capability", "action_type"):
        assert param not in signature.parameters, f"operator must not expose a {param} override"

    decision = registry.get("valo.public.issue_public_decision@1.0.0")
    assert decision.risk_class.value == "R4_RIGHTS_IMPACTING"


def test_postconditions_come_from_registered_definition() -> None:
    """Postconditions cannot be removed or changed by the caller: they are part
    of the registered Function's workflow config."""
    registry, *_ = _public_parts()
    pay_workflow = registry.graph_for(registry.get("valo.finance.pay@1.0.0"))
    execute = [n for n in pay_workflow.nodes if n.node_class.value == "WRITE"][0]
    assert execute.config.get("postconditions") == {"payment": "VERIFIED"}
    signature = inspect.signature(act)
    assert "postconditions" not in signature.parameters


def test_idempotency_policy_comes_from_registered_definition() -> None:
    """The registered NOTIFY Function requires an idempotency key; the operator
    cannot strip it. The Gateway dedups by the deterministically derived key,
    so a replayed submission never doubles the external effect."""
    from valo_public_pack.ports import PublicGateway
    from valo_workflow_isa.contracts import IdempotencyPolicy
    from valo_workflow_isa.stdlib.keys import derive_idempotency_key

    registry, *_ = _public_parts()
    notify = registry.get("valo.public.notify@1.0.0")
    assert notify.idempotency_requirement.value == "VERIFY_BEFORE_REPLAY", "NOTIFY must require a key"

    inputs = {"notification": {"recipient": "applicant-1", "message": "decision"}}
    key = derive_idempotency_key(IdempotencyPolicy(require_key=True), inputs)
    gateway = PublicGateway()
    gateway.execute("binding:1", {"action_type": "NOTIFY"}, key)
    gateway.execute("binding:1", {"action_type": "NOTIFY"}, key)
    assert len([e for e in gateway.executions if e.get("action_type") == "NOTIFY"]) == 1


def test_double_submission_no_double_external_effect() -> None:
    """After a NOTIFY the case advanced to NOTIFIED; a second submission of the
    same action is rejected by the state machine BEFORE the Gateway — the
    external effect is never doubled."""
    registry, adapter, reht, gateway, veritas, baro, kernel = _public_parts()

    def run(function_id, inputs):
        return act(registry, adapter, reht, gateway, veritas, baro, function_id=function_id, inputs=inputs)

    run("valo.public.register_case", {"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}})
    run("valo.public.mark_ready_for_review", {"case": {"id": "case-1"}})
    run("valo.public.mark_under_review", {"case": {"id": "case-1"}})
    run("valo.public.mark_ready_for_decision", {"case": {"id": "case-1"}})
    issued = run("valo.public.issue_public_decision", {"context": {"case": "case-1"}})
    assert issued.decision == "ALLOW"

    first = run("valo.public.notify", {"notification": {"recipient": "applicant-1", "message": "decision"}})
    assert first.decision == "ALLOW"
    assert first.gateway_executions == 1

    second = run("valo.public.notify", {"notification": {"recipient": "applicant-1", "message": "decision"}})
    assert second.status == "FAILED", "second submission must be rejected"
    assert second.decision is None
    assert second.gateway_executions == 0, "the external effect must never be doubled"
    assert kernel.state().entities["case-1"].state == "NOTIFIED"


def test_snapshot_public() -> None:
    _, _, _, _, _, _, kernel = _public_parts()
    snap = operator_snapshot(kernel, pack_id="public")
    assert snap["summary"]["pack"] == "public"
    assert any(c["case_id"] == "case-1" for c in snap["summary"]["cases"])
    assert snap["summary"]["ready_for_decision"] == []


def test_snapshot_trades() -> None:
    _, _, _, _, _, _, kernel = _trades_parts()
    snap = operator_snapshot(kernel, pack_id="trades")
    assert snap["summary"]["pack"] == "trades"
    assert snap["summary"]["open_workorders"] == ["workorder-1"]


def test_deterministic_act() -> None:
    r1, a1, reht1, g1, v1, b1, k1 = _public_parts()
    r2, a2, reht2, g2, v2, b2, k2 = _public_parts()
    inputs = {"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}}
    res1 = act(r1, a1, reht1, g1, v1, b1, function_id="valo.public.register_case", inputs=inputs)
    res2 = act(r2, a2, reht2, g2, v2, b2, function_id="valo.public.register_case", inputs=inputs)
    assert res1.decision == res2.decision == "ALLOW"
    assert res1.gateway_executions == res2.gateway_executions == 1
    assert res1.effect_verified == res2.effect_verified is True

    # same context -> same permit (determinism of the boundary)
    r0, a0, reht0, _, _, _, _ = _public_parts()
    ctx = a0.execution_context(
        "public", "system-1", "ADMIN", "case-1", {"state": "REGISTERED"}, identity_id="id-system-1"
    )
    contract = {"capability": "ADMIN", "target": "case-1", "action_type": "REGISTER"}
    p1 = reht0.authorize(ctx, contract).permit_ref
    p2 = reht0.authorize(ctx, contract).permit_ref
    assert p1 == p2


def test_decision_correlated_to_instance() -> None:
    """P1: a reused REHT must not report a stale decision. A pre-execution
    rejection (before REHT) yields decision=None for that action, never the
    previous action's ALLOW."""
    registry, adapter, reht, gateway, veritas, baro, kernel = _public_parts()
    first = act(registry, adapter, reht, gateway, veritas, baro,
                function_id="valo.public.register_case",
                inputs={"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}})
    assert first.decision == "ALLOW"
    # second action stops BEFORE REHT: NOTIFY from REGISTERED is illegal
    # (pre-execution admissibility), so decision must be None, not the old ALLOW
    second = act(registry, adapter, reht, gateway, veritas, baro,
                 function_id="valo.public.notify",
                 inputs={"notification": {"recipient": "applicant-1", "message": "x"}})
    assert second.decision is None, "must not report a stale decision from a previous action"
    assert second.gateway_executions == 0
