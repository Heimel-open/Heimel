import pytest

from tests.conftest import make_chain
from valo_gateway import ValoGateway
from valo_gateway.gateway import ControlEvent, ControlEventType, RuntimeControlPlane
from valo_gateway.tool_adapters import FunctionTool


def test_public_gateway_fails_closed_without_authoritative_control_plane():
    now, authority, action, clearance, permit = make_chain()
    calls = []

    with pytest.raises(ValueError, match="fresh authoritative control plane"):
        ValoGateway().execute(
            authority=authority,
            clearance=clearance,
            permit=permit,
            action=action,
            executor_id="killer-trial",
            tool=FunctionTool("effect", lambda: calls.append("effect")),
            now=now,
        )

    assert calls == []
    assert permit.consumed_at is None


def test_canonical_revocation_blocks_stale_caller_envelope():
    now, authority, action, clearance, permit = make_chain()
    control = RuntimeControlPlane()
    gateway = ValoGateway(control_plane=control)
    calls = []

    control.apply(
        ControlEvent(
            event_type=ControlEventType.REVOKE_AUTHORITY,
            issuer_id="canonical-authority-store",
            reason="killer-trial regression",
            authority_envelope_id=authority.envelope_id,
        )
    )

    with pytest.raises(ValueError, match="revocation or HALT"):
        gateway.execute(
            authority=authority,
            clearance=clearance,
            permit=permit,
            action=action,
            executor_id="killer-trial",
            tool=FunctionTool("effect", lambda: calls.append("effect")),
            now=now,
        )

    assert calls == []
    assert permit.consumed_at is None
