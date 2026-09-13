"""Vendor neutrality: the SAME Operator chain drives TWO different vendor
protocols purely via configuration. Vendor differences (auth headers,
idempotency-header names, paths, state fields, success states) are absorbed in
the ConfiguredGateway/ConfiguredVeritas + VendorConfig — no VALO architecture
change, no adapter-side authorization.
"""

from __future__ import annotations

import json
import urllib.request

from valo_operator import OperatorRequest, build_public_runtime, build_trades_runtime
from valo_operator.adapters import (
    MESSAGING_VENDOR,
    PAYMENTS_VENDOR,
    ConfiguredGateway,
    ConfiguredVeritas,
    spawn_service,
)


def _advance_public_to_decided(runtime) -> None:
    for fid, inputs, cid in [
        ("valo.public.register_case", {"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}}, "p1"),
        ("valo.public.mark_ready_for_review", {"case": {"id": "case-1"}}, "p2"),
        ("valo.public.mark_under_review", {"case": {"id": "case-1"}}, "p3"),
        ("valo.public.mark_ready_for_decision", {"case": {"id": "case-1"}}, "p4"),
    ]:
        runtime.submit(OperatorRequest(correlation_id=cid, function_id=fid, inputs=inputs))
    issued = runtime.submit(OperatorRequest(
        correlation_id="p5", function_id="valo.public.issue_public_decision",
        inputs={"context": {"case": "case-1"}},
    ))
    assert issued.decision == "ALLOW"


def test_vendor_auth_header_is_sent_and_enforced() -> None:
    svc = spawn_service("valo_operator.adapters.services.vendor", ready_prefix="VENDOR_READY")
    try:
        config = PAYMENTS_VENDOR(svc.base_url)
        gateway = ConfiguredGateway(config)
        result = gateway.execute("binding:1", {"action_type": "PAY"}, "key-auth")
        assert result.success is True, "the configured adapter must send the vendor auth header"

        # without the vendor auth header the service rejects with 401
        try:
            request = urllib.request.Request(
                f"{svc.base_url}/v1/payments",
                data=json.dumps({"id": "x"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(request, timeout=5)
            raise AssertionError("the vendor must reject unauthenticated requests")
        except urllib.error.HTTPError as exc:
            assert exc.code == 401
    finally:
        svc.stop()


def test_payments_vendor_allows_and_independently_verifies() -> None:
    svc = spawn_service("valo_operator.adapters.services.vendor", ready_prefix="VENDOR_READY")
    try:
        config = PAYMENTS_VENDOR(svc.base_url)
        runtime = build_trades_runtime(gateway=ConfiguredGateway(config), veritas=ConfiguredVeritas(config))
        result = runtime.submit(OperatorRequest(
            correlation_id="pay-1", function_id="valo.trades.receive_payment",
            inputs={"obligation": {"invoice_id": "inv-1", "amount": "16500.00"}},
        ))
        assert result.decision == "ALLOW"
        assert result.effect_verified is True
        assert result.receipts and any(r["kind"] == "effect_verified" for r in result.receipts)
    finally:
        svc.stop()


def test_messaging_vendor_allows_and_independently_verifies() -> None:
    svc = spawn_service("valo_operator.adapters.services.vendor", ready_prefix="VENDOR_READY")
    try:
        config = MESSAGING_VENDOR(svc.base_url)
        runtime = build_public_runtime(gateway=ConfiguredGateway(config), veritas=ConfiguredVeritas(config))
        _advance_public_to_decided(runtime)
        result = runtime.submit(OperatorRequest(
            correlation_id="msg-1", function_id="valo.public.notify",
            inputs={"notification": {"recipient": "applicant-1", "message": "decision"}},
        ))
        assert result.decision == "ALLOW"
        assert result.effect_verified is True
        assert runtime.kernel.state().entities["case-1"].state == "NOTIFIED"
    finally:
        svc.stop()


def test_vendor_idempotency_header_dedups() -> None:
    svc = spawn_service("valo_operator.adapters.services.vendor", ready_prefix="VENDOR_READY")
    try:
        config = PAYMENTS_VENDOR(svc.base_url)
        gateway = ConfiguredGateway(config)
        gateway.execute("binding:1", {"action_type": "PAY"}, "key-idem")
        replay = gateway.execute("binding:1", {"action_type": "PAY"}, "key-idem")
        assert replay.external_id == "replayed"
        assert len(gateway.executions) == 1, "retry must not double the external effect"
    finally:
        svc.stop()


def test_vendor_unknown_outcome_never_synthetic_success() -> None:
    """A vendor state path that does not resolve (e.g. the record id scheme
    differs) yields UNKNOWN — never a synthetic success."""
    svc = spawn_service("valo_operator.adapters.services.vendor", ready_prefix="VENDOR_READY")
    try:
        config = PAYMENTS_VENDOR(svc.base_url)
        runtime = build_trades_runtime(gateway=ConfiguredGateway(config), veritas=ConfiguredVeritas(config))
        result = runtime.submit(OperatorRequest(
            correlation_id="pay-2", function_id="valo.trades.receive_payment",
            inputs={"obligation": {"invoice_id": "inv-1", "amount": "16500.00"}},
        ))
        # the gateway recorded the id; veritas re-reads it from the vendor path
        assert result.effect_verified is True  # payments vendor resolves fine
        # now a MISCONFIGURED veritas (wrong state path) must not invent success
        broken = PAYMENTS_VENDOR(svc.base_url)
        broken = type(broken)(
            name=broken.name, base_url=broken.base_url, send_path=broken.send_path,
            auth_header=broken.auth_header, idempotency_header=broken.idempotency_header,
            id_field=broken.id_field, state_path="/nope/{id}", state_field=broken.state_field,
            success_state=broken.success_state, effect_key=broken.effect_key,
        )
        runtime2 = build_trades_runtime(gateway=ConfiguredGateway(config), veritas=ConfiguredVeritas(broken))
        result2 = runtime2.submit(OperatorRequest(
            correlation_id="pay-3", function_id="valo.trades.receive_payment",
            inputs={"obligation": {"invoice_id": "inv-1", "amount": "16500.00"}},
        ))
        assert result2.effect_verified is False, "an unresolved observation must never be a synthetic success"
        assert result2.status == "FAILED"
    finally:
        svc.stop()


def test_same_operator_contract_drives_both_vendors() -> None:
    import inspect

    from valo_operator.adapters import vendor

    # structural: no adapter-side authorization in the vendor layer
    assert "capability" not in inspect.getsource(vendor)

    svc = spawn_service("valo_operator.adapters.services.vendor", ready_prefix="VENDOR_READY")
    try:
        payments = PAYMENTS_VENDOR(svc.base_url)
        messaging = MESSAGING_VENDOR(svc.base_url)

        trades = build_trades_runtime(gateway=ConfiguredGateway(payments), veritas=ConfiguredVeritas(payments))
        pay = trades.submit(OperatorRequest(
            correlation_id="v-pay", function_id="valo.trades.receive_payment",
            inputs={"obligation": {"invoice_id": "inv-1", "amount": "16500.00"}},
        ))
        assert pay.decision == "ALLOW" and pay.effect_verified is True

        public = build_public_runtime(gateway=ConfiguredGateway(messaging), veritas=ConfiguredVeritas(messaging))
        _advance_public_to_decided(public)
        msg = public.submit(OperatorRequest(
            correlation_id="v-msg", function_id="valo.public.notify",
            inputs={"notification": {"recipient": "applicant-1", "message": "decision"}},
        ))
        assert msg.decision == "ALLOW" and msg.effect_verified is True
    finally:
        svc.stop()
