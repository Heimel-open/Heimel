from __future__ import annotations

from valo_operator import OperatorRequest
from valo_operator.adapters import ExternalSystem, HttpGateway, HttpVeritas


def _advance_to_decided(runtime) -> None:
    runtime.submit(OperatorRequest(
        correlation_id="a1", function_id="valo.public.register_case",
        inputs={"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}},
    ))
    runtime.submit(OperatorRequest(
        correlation_id="a2", function_id="valo.public.mark_ready_for_review",
        inputs={"case": {"id": "case-1"}},
    ))
    runtime.submit(OperatorRequest(
        correlation_id="a3", function_id="valo.public.mark_under_review",
        inputs={"case": {"id": "case-1"}},
    ))
    runtime.submit(OperatorRequest(
        correlation_id="a4", function_id="valo.public.mark_ready_for_decision",
        inputs={"case": {"id": "case-1"}},
    ))
    issued = runtime.submit(OperatorRequest(
        correlation_id="a5", function_id="valo.public.issue_public_decision",
        inputs={"context": {"case": "case-1"}},
    ))
    assert issued.decision == "ALLOW"


def _notify_request():
    return OperatorRequest(
        correlation_id="notify-1", function_id="valo.public.notify",
        inputs={"notification": {"recipient": "applicant-1", "message": "decision"}},
    )


def test_production_adapter_delivered() -> None:
    from valo_operator import build_public_runtime

    external = ExternalSystem(landing="DELIVERED")
    try:
        runtime = build_public_runtime(
            gateway=HttpGateway(external.base_url),
            veritas=HttpVeritas(external.base_url),
        )
        _advance_to_decided(runtime)
        result = runtime.submit(_notify_request())
        assert result.decision == "ALLOW"
        assert result.status == "COMPLETED"
        assert result.effect_verified is True
        assert runtime.kernel.state().entities["case-1"].state == "NOTIFIED"
    finally:
        external.stop()


def test_production_adapter_http200_not_delivered() -> None:
    """HTTP 200 from the send is NOT delivered: the external system accepted
    the request but the record is PENDING. Veritas observes reality and BARO
    diverges — no EffectVerified, no NOTIFIED transition."""
    from valo_operator import build_public_runtime

    external = ExternalSystem(landing="DELIVERED", landing_by_action={"NOTIFY": "PENDING"})
    try:
        runtime = build_public_runtime(
            gateway=HttpGateway(external.base_url),
            veritas=HttpVeritas(external.base_url),
        )
        _advance_to_decided(runtime)
        result = runtime.submit(_notify_request())
        assert result.status == "FAILED"
        assert "postcondition divergence" in str(result.errors)
        assert result.effect_verified is False
        assert runtime.kernel.state().entities["case-1"].state == "DECIDED"
    finally:
        external.stop()


def test_production_adapter_idempotent_replay() -> None:
    """Double submission of the same NOTIFY hits the external system once: the
    external service dedups by the record id, and the local gateway reuses the
    idempotency key."""
    from valo_operator import build_public_runtime

    external = ExternalSystem(landing="DELIVERED")
    try:
        runtime = build_public_runtime(
            gateway=HttpGateway(external.base_url),
            veritas=HttpVeritas(external.base_url),
        )
        _advance_to_decided(runtime)
        first = runtime.submit(_notify_request())
        assert first.decision == "ALLOW"
        notify_records = [r for r in external.records.values() if r.get("action_type") == "NOTIFY"]
        assert len(notify_records) == 1, "the external system must hold exactly one NOTIFY record"

        second = runtime.submit(_notify_request())
        assert second.status == "FAILED"  # state already NOTIFIED -> pre-execution reject
        assert len([r for r in external.records.values() if r.get("action_type") == "NOTIFY"]) == 1
    finally:
        external.stop()


def test_production_adapter_network_failure() -> None:
    """The external system is unreachable: the Gateway reports success=False,
    so the node fails with zero Kernel transition and no EffectVerified."""
    from valo_operator import build_public_runtime

    runtime = build_public_runtime(
        gateway=HttpGateway("http://127.0.0.1:1"),  # nothing listens here
        veritas=HttpVeritas("http://127.0.0.1:1"),
    )
    result = runtime.submit(OperatorRequest(
        correlation_id="net-1", function_id="valo.public.register_case",
        inputs={"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}},
    ))
    assert result.status == "FAILED"
    assert result.effect_verified is False
    assert runtime.kernel.state().entities["case-1"].state == "RECEIVED"


def test_external_system_dedups_by_id() -> None:
    external = ExternalSystem(landing="DELIVERED")
    try:
        gateway = HttpGateway(external.base_url)
        gateway.execute("binding:1", {"action_type": "NOTIFY"}, "key-x")
        r2 = gateway.execute("binding:1", {"action_type": "NOTIFY"}, "key-x")
        assert r2.external_id == "replayed"
        assert len(external.records) == 1
    finally:
        external.stop()
