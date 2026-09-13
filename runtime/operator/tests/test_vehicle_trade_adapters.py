from __future__ import annotations

import json

from valo_operator.adapters import (
    ConfiguredVeritas,
    vehicle_trade_edge_configured,
    vehicle_trade_external_config,
)
from valo_workflow_isa.ports import ExecutionResult


def test_vehicle_purchase_config_is_environment_driven(monkeypatch):
    monkeypatch.setenv("VEHICLE_PURCHASE_BASE_URL", "https://purchase.example")
    monkeypatch.setenv("VEHICLE_PURCHASE_AUTH", "Bearer secret-ref-runtime")
    monkeypatch.setenv("VEHICLE_PURCHASE_SEND_PATH", "/buy")
    monkeypatch.setenv("VEHICLE_PURCHASE_SUCCESS_STATE", "completed")

    config = vehicle_trade_external_config("purchase")

    assert config.base_url == "https://purchase.example"
    assert config.send_path == "/buy"
    assert config.success_state == "completed"
    assert config.effect_key == "vehicle_purchase_verified"
    assert vehicle_trade_edge_configured("purchase") is True


def test_vehicle_trade_payloads_are_transport_only(monkeypatch):
    monkeypatch.setenv("VEHICLE_SALE_BASE_URL", "https://sale.example")
    config = vehicle_trade_external_config("sale")
    body = config.body_builder(
        {
            "action_type": "RETAIL_VEHICLE_ACCEPT_SALE",
            "authority": {"should_not": "cross_transport_boundary"},
            "parameters": {
                "vehicle_trade": {
                    "vehicle_ref": "vehicle:1",
                    "listing_ref": "listing:1",
                    "buyer_ref": "buyer:1",
                    "amount_minor": 1_400_000,
                    "currency": "NOK",
                    "payment_method_ref": "payment-method:1",
                    "title_transfer_ref": "title:1",
                }
            },
        }
    )

    assert body["vehicle_ref"] == "vehicle:1"
    assert body["amount_minor"] == 1_400_000
    assert "authority" not in body


def test_all_vehicle_edges_have_independent_idempotent_routes():
    expected = {
        "purchase": ("/v1/vehicle/purchases", "purchased"),
        "transport": ("/v1/vehicle/transports", "booked"),
        "export": ("/v1/vehicle/exports", "exported"),
        "sale": ("/v1/vehicle/sales", "sold"),
    }
    for operation, (path, success) in expected.items():
        config = vehicle_trade_external_config(operation, base_url="https://edge.example")
        assert config.send_path == path
        assert config.state_path == f"{path}/{{id}}"
        assert config.success_state == success
        assert config.idempotency_header == "Idempotency-Key"
        assert config.effect_key == f"vehicle_{operation}_verified"


def test_generic_vehicle_effect_requires_exact_success_state(monkeypatch):
    config = vehicle_trade_external_config("purchase", base_url="https://edge.example")
    execution = ExecutionResult(
        success=True,
        external_id="purchase-1",
        receipt_ref="receipt-1",
        payload={"external_record_id": "purchase-1"},
    )

    class Response:
        def __init__(self, status):
            self.status = status

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self):
            return json.dumps({"id": "purchase-1", "status": self.status}).encode()

    monkeypatch.setattr(
        "valo_operator.adapters.vendor.urllib.request.urlopen",
        lambda request, timeout=5: Response("failed"),
    )
    failed = ConfiguredVeritas(config).observe(
        execution,
        {"action_type": "RETAIL_VEHICLE_PURCHASE"},
    )
    assert failed.observed["outcome"] == "NOT_VERIFIED"
    assert failed.observed["vehicle_purchase_verified"] is False

    monkeypatch.setattr(
        "valo_operator.adapters.vendor.urllib.request.urlopen",
        lambda request, timeout=5: Response("purchased"),
    )
    verified = ConfiguredVeritas(config).observe(
        execution,
        {"action_type": "RETAIL_VEHICLE_PURCHASE"},
    )
    assert verified.observed["outcome"] == "VERIFIED"
    assert verified.observed["vehicle_purchase_verified"] is True
