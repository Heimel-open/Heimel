from vacs.src.efficiency_engine import (
    Baseline,
    EfficiencyDecision,
    Observation,
    VALOEfficiencyEngine,
    ValueCreated,
    VerificationLevel,
    WorkCost,
)


def baseline(**overrides):
    data = dict(
        baseline_id="baseline_001",
        description="manual monthly report",
        prior_cost_usd=100.0,
        prior_duration_minutes=60.0,
        prior_error_rate=0.03,
        sample_size=5,
    )
    data.update(overrides)
    return Baseline(**data)


def observation(**overrides):
    data = dict(
        observation_id="obs_001",
        baseline_id="baseline_001",
        actual_cost=WorkCost(model_cost_usd=5.0, review_cost_usd=10.0, human_time_cost_usd=10.0),
        value_created=ValueCreated(time_saved_usd=80.0, cost_avoided_usd=20.0),
        actual_duration_minutes=12.0,
        actual_error_rate=0.02,
        usage_count=3,
        evidence_receipt_id="receipt_001",
    )
    data.update(overrides)
    return Observation(**data)


def test_verified_value_receives_credit():
    engine = VALOEfficiencyEngine()

    result = engine.evaluate(baseline(), observation())

    assert result.decision == EfficiencyDecision.CREDIT
    assert result.total_cost_of_work_usd == 25.0
    assert result.verified_value_created_usd == 100.0
    assert result.efficiency_score == 4.0
    assert result.net_value_usd == 75.0


def test_claim_without_evidence_does_not_receive_credit():
    engine = VALOEfficiencyEngine()

    result = engine.evaluate(
        baseline(sample_size=1),
        observation(usage_count=1, evidence_receipt_id=""),
        verification_level=VerificationLevel.CLAIMED,
    )

    assert result.decision == EfficiencyDecision.DEFER


def test_observed_but_not_verified_waits_for_more_evidence():
    engine = VALOEfficiencyEngine()

    result = engine.evaluate(
        baseline(),
        observation(usage_count=2, evidence_receipt_id="receipt_001"),
        verification_level=VerificationLevel.OBSERVED,
    )

    assert result.decision == EfficiencyDecision.OBSERVE
    assert result.verified_value_created_usd == 70.0


def test_error_rate_increase_rejects_value():
    engine = VALOEfficiencyEngine()

    result = engine.evaluate(
        baseline(prior_error_rate=0.01),
        observation(actual_error_rate=0.10),
    )

    assert result.decision == EfficiencyDecision.DENY
    assert "error rate" in result.reason


def test_negative_net_value_is_denied():
    engine = VALOEfficiencyEngine()

    result = engine.evaluate(
        baseline(),
        observation(
            actual_cost=WorkCost(model_cost_usd=50.0, review_cost_usd=100.0),
            value_created=ValueCreated(time_saved_usd=20.0),
        ),
    )

    assert result.decision == EfficiencyDecision.DENY


def test_receipt_contains_value_metrics():
    engine = VALOEfficiencyEngine()
    result = engine.evaluate(baseline(), observation())
    receipt = engine.receipt(result)

    assert receipt["type"] == "valo.efficiency_engine.receipt.v1"
    assert receipt["decision"] == "CREDIT"
    assert receipt["tcw_usd"] == 25.0
    assert receipt["vvc_usd"] == 100.0
    assert receipt["ves"] == 4.0
    assert receipt["payload_hash"].startswith("sha256:")
