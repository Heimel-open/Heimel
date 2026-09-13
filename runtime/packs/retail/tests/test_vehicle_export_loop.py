from __future__ import annotations

import valo_retail_pack
from valo_retail_pack import (
    Decision,
    RetailAction,
    VEHICLE_FUNCTION_IDS,
    VehicleExportMission,
    VehicleStageRequest,
    build_retail_registry,
    build_vehicle_intent,
    evaluate_retail_intent,
    next_vehicle_action,
    vehicle_trade_payload,
)


def mission(**overrides):
    values = dict(
        tenant_id="vehicle-export",
        actor_id="vehicle-export-agent",
        authority_chain=("owner:nsolland", "delegation:vehicle-export"),
        purpose="vehicle-export-margin",
        jurisdiction="NO",
        resource_id="vehicle:TV91922",
        candidate_ref="baro:candidate:TV91922",
        currency="NOK",
        expected_net_profit_minor=500_000,
        min_net_profit_minor=100_000,
        autonomy_limit_minor=2_000_000,
        authority_limit_minor=3_000_000,
        risk_score=0.4,
        evidence_refs=("baro:analysis:TV91922", "tax:refund:TV91922"),
    )
    values.update(overrides)
    return VehicleExportMission(**values)


def request(action, value_minor, metadata, key="stage:1"):
    return VehicleStageRequest(
        action=action,
        value_minor=value_minor,
        metadata=metadata,
        valid_until_ns=10_000,
        idempotency_key=key,
        evidence_refs=(f"evidence:{key}",),
    )


def purchase(**metadata):
    base = {
        "seller_id": "seller:1",
        "purchase_price_minor": 800_000,
        "market_evidence_fresh": True,
        "refund_evidence_ref": "tax:refund:TV91922",
        "foreign_value_evidence_ref": "market:eu:TV91922",
    }
    base.update(metadata)
    return request(RetailAction.VEHICLE_PURCHASE, int(base["purchase_price_minor"]), base)


def test_vehicle_lifecycle_order_is_deterministic():
    status = "CANDIDATE"
    expected = [
        RetailAction.VEHICLE_PURCHASE,
        RetailAction.VEHICLE_BOOK_TRANSPORT,
        RetailAction.VEHICLE_EXPORT,
        RetailAction.VEHICLE_LIST_SALE,
        RetailAction.VEHICLE_ACCEPT_SALE,
        RetailAction.VEHICLE_SETTLE_SALE,
    ]
    seen = []
    transitions = {
        RetailAction.VEHICLE_PURCHASE: "PURCHASED",
        RetailAction.VEHICLE_BOOK_TRANSPORT: "IN_TRANSIT",
        RetailAction.VEHICLE_EXPORT: "EXPORTED",
        RetailAction.VEHICLE_LIST_SALE: "LISTED",
        RetailAction.VEHICLE_ACCEPT_SALE: "SALE_AGREED",
        RetailAction.VEHICLE_SETTLE_SALE: "SOLD",
    }
    while (action := next_vehicle_action(status)) is not None:
        seen.append(action)
        status = transitions[action]
    assert seen == expected
    assert status == "SOLD"


def test_purchase_inside_mandate_is_admissible_before_operator_submit():
    intent = build_vehicle_intent(
        mission(),
        purchase(),
        before_state={"status": "CANDIDATE", "version": "1"},
    )
    result = evaluate_retail_intent(intent, now_ns=100)
    assert result.decision is Decision.ALLOW


def test_purchase_over_autonomy_limit_steps_up_before_operator_submit():
    req = purchase(purchase_price_minor=2_500_000)
    intent = build_vehicle_intent(
        mission(),
        req,
        before_state={"status": "CANDIDATE", "version": "1"},
    )
    result = evaluate_retail_intent(intent, now_ns=100)
    assert result.decision is Decision.STEP_UP


def test_stale_purchase_economics_defer_before_operator_submit():
    intent = build_vehicle_intent(
        mission(),
        purchase(market_evidence_fresh=False),
        before_state={"status": "CANDIDATE", "version": "1"},
    )
    result = evaluate_retail_intent(intent, now_ns=100)
    assert result.decision is Decision.DEFER


def test_export_classified_as_waste_is_denied():
    req = request(
        RetailAction.VEHICLE_EXPORT,
        20_000,
        {
            "export_destination": "DE",
            "declaration_ref": "customs:1",
            "vehicle_export_eligible": True,
            "waste_classification": "WASTE",
        },
    )
    intent = build_vehicle_intent(
        mission(),
        req,
        before_state={"status": "IN_TRANSIT", "version": "3"},
    )
    result = evaluate_retail_intent(intent, now_ns=100)
    assert result.decision is Decision.DENY


def test_operator_payload_binds_economics_evidence_and_expected_state():
    payload = vehicle_trade_payload(
        mission(),
        purchase(),
        before_state={"status": "CANDIDATE", "version": "1"},
    )
    assert payload["vehicle_ref"] == "vehicle:TV91922"
    assert payload["candidate_ref"] == "baro:candidate:TV91922"
    assert payload["value_minor"] == 800_000
    assert payload["expected_net_profit_minor"] == 500_000
    assert payload["desired_status"] == "PURCHASED"
    assert "baro:analysis:TV91922" in payload["evidence_refs"]


def test_vehicle_functions_are_registered_write_boundaries():
    registry = build_retail_registry()
    assert len(VEHICLE_FUNCTION_IDS) == 6
    for function_id in VEHICLE_FUNCTION_IDS:
        definition = registry.resolve(function_id, "1.0.0")
        graph = registry.graph_for(definition)
        assert [node.opcode for node in graph.nodes] == ["PREPARE_ACTION", "EXECUTE_ACTION"]
        execute = graph.node_map()["execute"]
        assert execute.policies.idempotency.require_key is True
        assert execute.policies.idempotency.verify_before_replay is True
        assert execute.config["target"] == "vehicle-export-portfolio"


def test_vehicle_pack_exports_no_direct_vehicle_agent_effect_path():
    assert not hasattr(valo_retail_pack, "VehicleExportAgent")
