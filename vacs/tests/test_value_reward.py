from vacs.src.value_reward import (
    CreatorType,
    RewardDecision,
    ValueClaim,
    VALOValueRewardGate,
)


def base_claim(**overrides):
    data = dict(
        claim_id="claim_001",
        beneficiary_id="employee_001",
        creator_type=CreatorType.HUMAN_AGENT_PAIR,
        source_action_id="action_001",
        source_receipt_id="receipt_001",
        value_claim_usd=100.0,
        value_basis="reusable workflow saves analyst time",
        confidence=0.90,
        risk_adjustment=10.0,
    )
    data.update(overrides)
    return ValueClaim(**data)


def test_allows_small_risk_adjusted_reward():
    gate = VALOValueRewardGate()

    result = gate.evaluate(base_claim())

    assert result.decision == RewardDecision.ALLOW
    assert result.reward_units == 9.0


def test_defers_without_source_receipt():
    gate = VALOValueRewardGate()

    result = gate.evaluate(base_claim(source_receipt_id=""))

    assert result.decision == RewardDecision.DEFER


def test_defers_low_confidence_value_claim():
    gate = VALOValueRewardGate()

    result = gate.evaluate(base_claim(confidence=0.40))

    assert result.decision == RewardDecision.DEFER


def test_denies_claim_below_risk_adjusted_threshold():
    gate = VALOValueRewardGate()

    result = gate.evaluate(base_claim(value_claim_usd=5.0, risk_adjustment=5.0))

    assert result.decision == RewardDecision.DENY


def test_steps_up_large_value_claim():
    gate = VALOValueRewardGate()

    result = gate.evaluate(base_claim(value_claim_usd=1000.0, risk_adjustment=50.0))

    assert result.decision == RewardDecision.STEP_UP


def test_reuse_and_spend_reduction_increase_reward():
    gate = VALOValueRewardGate()

    plain = gate.evaluate(base_claim())
    boosted = gate.evaluate(base_claim(reusable=True, reduces_remote_spend=True, creates_audit_evidence=True))

    assert boosted.reward_units > plain.reward_units


def test_receipt_contains_reward_fields():
    gate = VALOValueRewardGate()
    result = gate.evaluate(base_claim(reusable=True))
    receipt = gate.receipt(result)

    assert receipt["type"] == "valo.value_reward.receipt.v1"
    assert receipt["beneficiary_id"] == "employee_001"
    assert receipt["creator_type"] == "human_agent_pair"
    assert receipt["reward_unit"] == "VALO_CREDIT"
    assert receipt["payload_hash"].startswith("sha256:")
