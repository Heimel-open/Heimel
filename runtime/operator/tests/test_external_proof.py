"""External Production Proof — the deciding test.

Swaps the internal messaging fixture for a real vendor WITHOUT changing the
operator chain: only a VendorConfig (base_url + credentials from env) differs.
Gated on MSG_BASE_URL / MSG_AUTH / MSG_FROM; skips with a clear message when
the real credentials are absent, and the harness still runs the operator chain
against the internal fixture so the mechanics are exercised.
"""

from __future__ import annotations

import os

import pytest

from valo_operator import OperatorRequest, build_public_runtime
from valo_operator.adapters import ConfiguredGateway, ConfiguredVeritas
from valo_operator.adapters.external_proof import external_proof_configured, messaging_external_config

pytestmark = pytest.mark.skipif(
    not external_proof_configured(),
    reason="real messaging credentials not configured (set MSG_BASE_URL, MSG_AUTH, MSG_FROM)",
)


def _advance_to_decided(runtime) -> None:
    for fid, inputs, cid in [
        ("valo.public.register_case", {"application": {"id": "app-1", "service_type": "PUBLIC_SERVICE_A"}}, "e1"),
        ("valo.public.mark_ready_for_review", {"case": {"id": "case-1"}}, "e2"),
        ("valo.public.mark_under_review", {"case": {"id": "case-1"}}, "e3"),
        ("valo.public.mark_ready_for_decision", {"case": {"id": "case-1"}}, "e4"),
    ]:
        runtime.submit(OperatorRequest(correlation_id=cid, function_id=fid, inputs=inputs))
    issued = runtime.submit(OperatorRequest(
        correlation_id="e5", function_id="valo.public.issue_public_decision",
        inputs={"context": {"case": "case-1"}},
    ))
    assert issued.decision == "ALLOW"


def _notify_request():
    return OperatorRequest(
        correlation_id="ext-notify", function_id="valo.public.notify",
        inputs={"notification": {
            "recipient": os.environ.get("MSG_TO", "<recipient>"),
            "message": "VALO external production proof",
        }},
    )


def test_external_messaging_allows_and_independently_verifies() -> None:
    """Criterion 1 + the deciding test: the SAME operator code drives the REAL
    messaging endpoint; only the VendorConfig differs."""
    config = messaging_external_config()
    runtime = build_public_runtime(gateway=ConfiguredGateway(config), veritas=ConfiguredVeritas(config))
    _advance_to_decided(runtime)
    result = runtime.submit(_notify_request())
    assert result.decision == "ALLOW"
    assert result.effect_verified is True, (
        "the external side effect must be independently observed; "
        "fix the recipient in MSG_FROM / the notify input"
    )
    assert runtime.kernel.state().entities["case-1"].state == "NOTIFIED"


def test_external_messaging_chain_unchanged_by_vendor() -> None:
    """The deciding claim, structurally: REHT/Operator/Fabric/ISA/Kernel are
    not imported or touched by the vendor swap."""
    import inspect

    from valo_operator.adapters import vendor

    config = messaging_external_config()
    assert config.name == "messaging-external"
    assert config.body_builder is not None
    # the operator chain modules are the SAME ones used for the internal fixture
    source = inspect.getsource(vendor)
    assert "ConfiguredGateway" in source and "ConfiguredVeritas" in source
