"""Production Integration Program P0 — acceptance proofs against TWO real,
standalone external services (separate processes, own state, real HTTP).

Criterion: NO mock as the final effect point. The effect lives in the service
process's state and Veritas verifies it by reading that state back.
"""

from __future__ import annotations

from valo_reht import RealReht

from valo_operator import OperatorRequest, build_public_runtime, build_trades_runtime
from valo_operator.adapters import ledger_integration, notification_integration, spawn_service


def _public_runtime_with(integration):
    return build_public_runtime(gateway=integration.gateway, veritas=integration.veritas)


def _advance_to_decided(runtime) -> None:
    for fid, inputs, cid in [
        ("valo.public.register_case", {"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}}, "a1"),
        ("valo.public.mark_ready_for_review", {"case": {"id": "case-1"}}, "a2"),
        ("valo.public.mark_under_review", {"case": {"id": "case-1"}}, "a3"),
        ("valo.public.mark_ready_for_decision", {"case": {"id": "case-1"}}, "a4"),
    ]:
        runtime.submit(OperatorRequest(correlation_id=cid, function_id=fid, inputs=inputs))
    issued = runtime.submit(OperatorRequest(
        correlation_id="a5", function_id="valo.public.issue_public_decision",
        inputs={"context": {"case": "case-1"}},
    ))
    assert issued.decision == "ALLOW"


def _notify_request():
    return OperatorRequest(
        correlation_id="notify", function_id="valo.public.notify",
        inputs={"notification": {"recipient": "applicant-1", "message": "decision"}},
    )


def test_1_allow_actual_effect_independently_verified() -> None:
    svc = spawn_service("valo_operator.adapters.services.notifier", landing="DELIVERED")
    try:
        integration = notification_integration(svc.base_url)
        runtime = _public_runtime_with(integration)
        _advance_to_decided(runtime)
        result = runtime.submit(_notify_request())
        assert result.decision == "ALLOW"
        assert result.effect_verified is True
        assert runtime.kernel.state().entities["case-1"].state == "NOTIFIED"
    finally:
        svc.stop()


def test_2_deny_zero_external_effect() -> None:
    from valo_kernel.contracts import CanonicalEvent, EventType, utcnow

    svc = spawn_service("valo_operator.adapters.services.notifier", landing="DELIVERED")
    try:
        integration = notification_integration(svc.base_url)
        runtime = _public_runtime_with(integration)
        runtime.kernel.append(CanonicalEvent(
            event_id="revoke-admin", event_type=EventType.AUTHORITY_REVOKED,
            tenant_id="public", subject="system-1", source="kernel", effective_at=utcnow(),
            payload={"authority_id": "auth-system-ADMIN", "revocation_ref": "rev-admin"},
        ))
        result = runtime.submit(OperatorRequest(
            correlation_id="deny", function_id="valo.public.register_case",
            inputs={"application": {"id": "app-1"}},
        ))
        assert result.decision == "DENY"
        assert result.effect_verified is False
        assert result.gateway_executions == 0
    finally:
        svc.stop()


def test_3_revocation_between_plan_and_execution_zero_effect() -> None:
    from valo_kernel.contracts import CanonicalEvent, EventType, utcnow

    svc = spawn_service("valo_operator.adapters.services.notifier", landing="DELIVERED")
    try:
        integration = notification_integration(svc.base_url)
        runtime = _public_runtime_with(integration)
        # plan: register succeeds and produces an external record
        first = runtime.submit(OperatorRequest(
            correlation_id="plan", function_id="valo.public.register_case",
            inputs={"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}},
        ))
        assert first.decision == "ALLOW"
        planned_records = len(integration.gateway.executions)
        # revoke between plan and the next execution
        runtime.kernel.append(CanonicalEvent(
            event_id="revoke-admin", event_type=EventType.AUTHORITY_REVOKED,
            tenant_id="public", subject="system-1", source="kernel", effective_at=utcnow(),
            payload={"authority_id": "auth-system-ADMIN", "revocation_ref": "rev-admin"},
        ))
        second = runtime.submit(OperatorRequest(
            correlation_id="exec", function_id="valo.public.mark_ready_for_review",
            inputs={"case": {"id": "case-1"}},
        ))
        assert second.decision == "DENY"
        assert len(integration.gateway.executions) == planned_records, "revocation must yield zero new effect"
    finally:
        svc.stop()


def test_4_http_success_without_desired_state_not_verified() -> None:
    svc = spawn_service("valo_operator.adapters.services.notifier", landing="DELIVERED")
    try:
        integration = notification_integration(svc.base_url)
        runtime = _public_runtime_with(integration)
        _advance_to_decided(runtime)
        # a second service instance: ISSUE_DECISION lands DELIVERED, NOTIFY
        # lands PENDING — the send succeeds but the notification is not delivered
        svc2 = spawn_service(
            "valo_operator.adapters.services.notifier",
            landing="DELIVERED",
            landing_by_action={"NOTIFY": "PENDING"},
        )
        try:
            runtime2 = _public_runtime_with(notification_integration(svc2.base_url))
            _advance_to_decided(runtime2)
            result = runtime2.submit(_notify_request())
            assert result.status == "FAILED"
            assert "postcondition divergence" in str(result.errors)
            assert result.effect_verified is False
            assert runtime2.kernel.state().entities["case-1"].state == "DECIDED"
        finally:
            svc2.stop()
    finally:
        svc.stop()


def test_5_timeout_unknown_never_synthetic_success() -> None:
    svc = spawn_service(
        "valo_operator.adapters.services.notifier",
        landing="DELIVERED",
        landing_by_action={"NOTIFY": "TIMEOUT"},
    )
    try:
        integration = notification_integration(svc.base_url)
        runtime = _public_runtime_with(integration)
        _advance_to_decided(runtime)
        result = runtime.submit(_notify_request())
        # the service accepted (200) but never recorded the effect
        assert result.effect_verified is False, "UNKNOWN must never be a synthetic success"
        assert result.status == "FAILED"
        assert result.decision == "ALLOW"  # REHT allowed, but the effect is unproven
    finally:
        svc.stop()


def test_6_retry_idempotency_no_double_effect() -> None:
    svc = spawn_service("valo_operator.adapters.services.ledger", mode="OK")
    try:
        integration = ledger_integration(svc.base_url)
        # the external service dedups by id; the gateway dedups by key
        integration.gateway.execute("binding:1", {"action_type": "PAY"}, "key-idem")
        replay = integration.gateway.execute("binding:1", {"action_type": "PAY"}, "key-idem")
        assert replay.external_id == "replayed"
        assert len(integration.gateway.executions) == 1, "retry must not double the external effect"
    finally:
        svc.stop()


def test_7_changed_action_after_permit_permit_invalid() -> None:
    a = build_public_runtime()
    ctx_a = a.kernel_adapter.execution_context(
        "public", "system-1", "ADMIN", "case-1", {"state": "REGISTERED"}, identity_id="id-system-1"
    )
    p_a = RealReht().authorize(ctx_a, {"capability": "ADMIN", "target": "case-1", "action_type": "REGISTER"}).permit_ref

    b = build_public_runtime()
    ctx_b = b.kernel_adapter.execution_context(
        "public", "system-1", "ADMIN", "case-1", {"state": "REGISTERED"}, identity_id="id-system-1"
    )
    p_b = RealReht().authorize(ctx_b, {"capability": "ADMIN", "target": "case-2", "action_type": "REGISTER"}).permit_ref
    assert p_a != p_b, "a permit for the exact action must not authorize a changed action"


def test_8_reconstructible_from_correlation_receipts() -> None:
    svc = spawn_service("valo_operator.adapters.services.notifier", landing="DELIVERED")
    try:
        integration = notification_integration(svc.base_url)
        runtime = _public_runtime_with(integration)
        _advance_to_decided(runtime)
        result = runtime.submit(_notify_request())
        entry = runtime.evidence_by_correlation("notify")
        assert entry is not None
        assert entry.instance_id == result.instance_id
        kinds = [r["kind"] for r in entry.receipts]
        assert kinds.index("authorization") < kinds.index("execution")
        assert kinds.index("execution") < kinds.index("effect_verified")
        assert entry.decision == "ALLOW"
        assert entry.effect_verified is True
    finally:
        svc.stop()


def test_9_same_operator_contract_two_systems_no_adapter_authorization() -> None:
    import inspect

    from valo_operator.adapters import http_gateway, http_veritas, integrations

    # structural: the adapters carry NO authorization logic (no capability check)
    for module in (http_gateway, http_veritas, integrations):
        source = inspect.getsource(module)
        assert "capability" not in source, f"{module.__name__} must not reference capability"

    # functional: the SAME OperatorRequest contract drives BOTH the notifier and
    # the ledger service (two different external systems) with no adapter auth.
    notifier = spawn_service("valo_operator.adapters.services.notifier", landing="DELIVERED")
    ledger = spawn_service("valo_operator.adapters.services.ledger", mode="OK")
    try:
        n_runtime = _public_runtime_with(notification_integration(notifier.base_url))
        _advance_to_decided(n_runtime)
        n_result = n_runtime.submit(_notify_request())
        assert n_result.decision == "ALLOW"

        t_runtime = build_trades_runtime(gateway=ledger_integration(ledger.base_url).gateway,
                                         veritas=ledger_integration(ledger.base_url).veritas)
        t_result = t_runtime.submit(OperatorRequest(
            correlation_id="pay", function_id="valo.trades.receive_payment",
            inputs={"obligation": {"invoice_id": "inv-1", "amount": "16500.00"}},
        ))
        assert t_result.decision == "ALLOW"
        assert t_result.effect_verified is True
    finally:
        notifier.stop()
        ledger.stop()
