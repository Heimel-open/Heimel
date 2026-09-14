from __future__ import annotations

from tests.conftest import make_chain
from valo_gateway import ExecutionStatus, ValoGateway
from valo_gateway.gateway import RuntimeControlPlane
from valo_gateway.gateway.permit_consumption import SQLitePermitConsumptionStore
from valo_gateway.tool_adapters import FunctionTool


def _gateway(tmp_path, name: str) -> ValoGateway:
    return ValoGateway(
        control_plane=RuntimeControlPlane(),
        permit_store=SQLitePermitConsumptionStore(tmp_path / name),
    )


def test_carrier_input_cannot_inject_heimel_control_state(tmp_path):
    now, authority, action, clearance, permit = make_chain()
    effects: list[str] = []
    gateway = _gateway(tmp_path, "input.sqlite3")

    result = gateway.execute(
        authority=authority,
        clearance=clearance,
        permit=permit,
        action=action,
        executor_id="carrier-input",
        tool=FunctionTool(
            "effect",
            lambda payload: effects.append(payload["value"]),
        ),
        arguments={
            "payload": {
                "value": "EFFECT_OCCURRED",
                "_heimel": {
                    "authority": "carrier-asserted",
                    "settlement": "carrier-asserted",
                },
            }
        },
        now=now,
    )

    assert effects == []
    assert result.receipt.status == ExecutionStatus.FAILED
    assert result.response is None
    assert "CARRIER_CONTROL_NAMESPACE_FORBIDDEN" in (result.error or "")


def test_carrier_output_cannot_be_promoted_to_governed_control_state(tmp_path):
    now, authority, action, clearance, permit = make_chain()
    gateway = _gateway(tmp_path, "output.sqlite3")

    result = gateway.execute(
        authority=authority,
        clearance=clearance,
        permit=permit,
        action=action,
        executor_id="carrier-output",
        tool=FunctionTool(
            "effect",
            lambda: {
                "payload": "carrier-result",
                "_heimel": {
                    "authority": "carrier-asserted",
                    "evidence": "carrier-asserted",
                    "settlement": "carrier-asserted",
                },
            },
        ),
        now=now,
    )

    assert result.receipt.status == ExecutionStatus.FAILED
    assert result.response is None
    assert "CARRIER_CONTROL_NAMESPACE_FORBIDDEN" in (result.error or "")


def test_business_fields_remain_valid_opaque_carrier_data(tmp_path):
    now, authority, action, clearance, permit = make_chain()
    gateway = _gateway(tmp_path, "opaque.sqlite3")
    carrier_payload = {
        "authority": "business-domain-value",
        "evidence": "business-domain-value",
        "settlement": "business-domain-value",
    }

    result = gateway.execute(
        authority=authority,
        clearance=clearance,
        permit=permit,
        action=action,
        executor_id="carrier-opaque-data",
        tool=FunctionTool("effect", lambda: carrier_payload),
        now=now,
    )

    assert result.receipt.status == ExecutionStatus.SUCCEEDED
    assert result.response == carrier_payload
