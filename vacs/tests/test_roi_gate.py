from vacs.src.roi_gate import ROIEstimate, ROIPolicy, ROIDecision, VALOROIGate


def test_allows_positive_low_cost_action():
    gate = VALOROIGate()
    estimate = ROIEstimate(
        action_id="draft-summary",
        expected_value_usd=5.00,
        estimated_cost_usd=0.25,
        confidence=0.95,
        value_basis="user time saved",
        cost_basis="model tokens",
    )

    result = gate.evaluate(estimate)

    assert result.decision == ROIDecision.ALLOW
    assert result.estimate.net_expected_value_usd == 4.75


def test_denies_negative_expected_value():
    gate = VALOROIGate()
    estimate = ROIEstimate(
        action_id="bulk-analysis",
        expected_value_usd=2.00,
        estimated_cost_usd=4.00,
        risk_cost_usd=1.00,
        confidence=0.90,
    )

    result = gate.evaluate(estimate)

    assert result.decision == ROIDecision.DENY
    assert "net expected value" in result.reason


def test_steps_up_expensive_positive_action():
    gate = VALOROIGate()
    estimate = ROIEstimate(
        action_id="full-customer-export-analysis",
        expected_value_usd=500.00,
        estimated_cost_usd=60.00,
        review_cost_usd=25.00,
        confidence=0.90,
    )
    policy = ROIPolicy(max_cost_without_step_up_usd=50.00)

    result = gate.evaluate(estimate, policy)

    assert result.decision == ROIDecision.STEP_UP


def test_defers_low_confidence():
    gate = VALOROIGate()
    estimate = ROIEstimate(
        action_id="unclear-request",
        expected_value_usd=20.00,
        estimated_cost_usd=1.00,
        confidence=0.40,
    )

    result = gate.evaluate(estimate)

    assert result.decision == ROIDecision.DEFER


def test_halts_irreversible_negative_value():
    gate = VALOROIGate()
    estimate = ROIEstimate(
        action_id="delete-records",
        expected_value_usd=1.00,
        estimated_cost_usd=3.00,
        confidence=0.95,
        reversible=False,
    )

    result = gate.evaluate(estimate)

    assert result.decision == ROIDecision.HALT


def test_receipt_contains_auditable_fields():
    gate = VALOROIGate()
    estimate = ROIEstimate(
        action_id="draft-summary",
        expected_value_usd=5.00,
        estimated_cost_usd=0.25,
        confidence=0.95,
    )
    result = gate.evaluate(estimate)
    receipt = gate.receipt(result, packet={"packet_id": "pkt_001"})

    assert receipt["type"] == "valo.roi_gate.receipt.v1"
    assert receipt["decision"] == "ALLOW"
    assert receipt["payload_hash"].startswith("sha256:")
    assert receipt["signature"].startswith("ed25519:")
