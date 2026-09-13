from vaig.rrp.receipt import ReceiptFactory


def test_receipt_for_action_binds_evidence_intent_thread():
    receipt = ReceiptFactory.create(
        receipt_id="rcp-2026-0616-001",
        evidence_condition_id="evc-2026-0616-001",
        evidence_condition_snapshot={"evidence_id": "evc-001", "validation_status": "validated"},
        intent_id="int-2026-0616-001",
        intent_snapshot={"intent_id": "int-001", "action_type": "FLIGHT_CLEARANCE"},
        vaig_outcome="ACTION",
        vaig_rule_triggered=None,
        vaig_rationale="Action permitted. No policy conflicts.",
        accountability_thread_id="thread-2026-0616-001",
        thread_snapshot={"thread_id": "thread-001", "events": []},
        final_status="EXECUTED",
    )

    assert receipt.receipt_id == "rcp-2026-0616-001"
    assert receipt.evidence_condition_id == "evc-2026-0616-001"
    assert receipt.intent_id == "int-2026-0616-001"
    assert receipt.vaig_outcome == "ACTION"
    assert receipt.final_status == "EXECUTED"


def test_receipt_for_refusal_binds_rrp_fields():
    receipt = ReceiptFactory.create(
        receipt_id="rcp-2026-0616-002",
        evidence_condition_id="evc-2026-0616-002",
        evidence_condition_snapshot={"evidence_id": "evc-002", "validation_status": "validated"},
        intent_id="int-2026-0616-002",
        intent_snapshot={"intent_id": "int-002", "action_type": "HARMFUL_GENERATION"},
        vaig_outcome="REFUSAL",
        vaig_rule_triggered="VAIG-SAF-003",
        vaig_rationale="Safety boundary violated.",
        accountability_thread_id="thread-2026-0616-002",
        thread_snapshot={"thread_id": "thread-002", "events": [{"sequence": 0}]},
        refusal_id="ref-2026-0616-002",
        refusal_snapshot={"refusal_id": "ref-002", "severity": "blocking"},
        uncertainty_inventory_id="inv-2026-0616-002",
        authority_assignment_id="asn-2026-0616-002",
        final_status="REFUSED",
    )

    assert receipt.vaig_outcome == "REFUSAL"
    assert receipt.refusal_id == "ref-2026-0616-002"
    assert receipt.uncertainty_inventory_id == "inv-2026-0616-002"
    assert receipt.authority_assignment_id == "asn-2026-0616-002"
    assert receipt.final_status == "REFUSED"


def test_receipt_is_queryable_by_layer_ids():
    receipt = ReceiptFactory.create(
        receipt_id="rcp-2026-0616-003",
        evidence_condition_id="evc-2026-0616-003",
        evidence_condition_snapshot={"evidence_id": "evc-003"},
        intent_id="int-2026-0616-003",
        intent_snapshot={"intent_id": "int-003"},
        vaig_outcome="ACTION",
        vaig_rule_triggered=None,
        vaig_rationale="",
        accountability_thread_id="thread-2026-0616-003",
        thread_snapshot={"thread_id": "thread-003"},
        final_status="EXECUTED",
    )

    assert receipt.evidence_condition_id == "evc-2026-0616-003"
    assert receipt.intent_id == "int-2026-0616-003"
    assert receipt.accountability_thread_id == "thread-2026-0616-003"
    assert receipt.to_dict()["receipt_id"] == "rcp-2026-0616-003"
