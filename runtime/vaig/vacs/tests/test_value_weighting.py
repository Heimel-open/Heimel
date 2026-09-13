from vacs.src.value_weighting import (
    AttributionLevel,
    DurationLevel,
    EvidenceLevel,
    StrategicLevel,
    VALOValueWeightingEngine,
    ValueWeightInput,
    WeightDecision,
)


def test_estimated_weekly_team_value_is_discounted_and_observed():
    engine = VALOValueWeightingEngine()
    value = ValueWeightInput(
        value_id="value_001",
        raw_value_usd=100_000.0,
        evidence_level=EvidenceLevel.ESTIMATED,
        duration_level=DurationLevel.WEEKLY,
        attribution_level=AttributionLevel.TEAM,
        strategic_level=StrategicLevel.NORMAL,
        has_baseline=True,
        source_receipt_id="receipt_001",
    )

    result = engine.evaluate(value)

    assert result.decision == WeightDecision.OBSERVE
    assert result.weighted_value_usd == 12_600.0


def test_verified_daily_direct_value_is_accepted_at_full_weight():
    engine = VALOValueWeightingEngine()
    value = ValueWeightInput(
        value_id="value_002",
        raw_value_usd=100_000.0,
        evidence_level=EvidenceLevel.VERIFIED,
        duration_level=DurationLevel.DAILY,
        attribution_level=AttributionLevel.DIRECT,
        strategic_level=StrategicLevel.NORMAL,
        has_baseline=True,
        source_receipt_id="receipt_002",
    )

    result = engine.evaluate(value)

    assert result.decision == WeightDecision.ACCEPT
    assert result.weighted_value_usd == 100_000.0


def test_cross_team_regulatory_value_gets_multiplier():
    engine = VALOValueWeightingEngine()
    value = ValueWeightInput(
        value_id="value_003",
        raw_value_usd=50_000.0,
        evidence_level=EvidenceLevel.VERIFIED,
        duration_level=DurationLevel.CROSS_TEAM_REUSE,
        attribution_level=AttributionLevel.DIRECT,
        strategic_level=StrategicLevel.REGULATORY_RISK,
        has_baseline=True,
        source_receipt_id="receipt_003",
    )

    result = engine.evaluate(value)

    assert result.decision == WeightDecision.ACCEPT
    assert result.weighted_value_usd == 150_000.0


def test_missing_baseline_defers_even_when_value_is_positive():
    engine = VALOValueWeightingEngine()
    value = ValueWeightInput(
        value_id="value_004",
        raw_value_usd=10_000.0,
        evidence_level=EvidenceLevel.VERIFIED,
        duration_level=DurationLevel.DAILY,
        attribution_level=AttributionLevel.DIRECT,
        strategic_level=StrategicLevel.NORMAL,
        has_baseline=False,
        source_receipt_id="receipt_004",
    )

    result = engine.evaluate(value)

    assert result.decision == WeightDecision.DEFER


def test_risk_and_extra_cost_reduce_weighted_value():
    engine = VALOValueWeightingEngine()
    value = ValueWeightInput(
        value_id="value_005",
        raw_value_usd=10_000.0,
        evidence_level=EvidenceLevel.VERIFIED,
        duration_level=DurationLevel.DAILY,
        attribution_level=AttributionLevel.DIRECT,
        strategic_level=StrategicLevel.NORMAL,
        risk_cost_usd=2_000.0,
        extra_cost_usd=1_000.0,
        has_baseline=True,
        source_receipt_id="receipt_005",
    )

    result = engine.evaluate(value)

    assert result.decision == WeightDecision.ACCEPT
    assert result.weighted_value_usd == 7_000.0


def test_receipt_contains_weight_components():
    engine = VALOValueWeightingEngine()
    value = ValueWeightInput(
        value_id="value_006",
        raw_value_usd=100_000.0,
        evidence_level=EvidenceLevel.ESTIMATED,
        duration_level=DurationLevel.WEEKLY,
        attribution_level=AttributionLevel.TEAM,
        strategic_level=StrategicLevel.NORMAL,
        has_baseline=True,
        source_receipt_id="receipt_006",
    )

    result = engine.evaluate(value)
    receipt = engine.receipt(result)

    assert receipt["type"] == "valo.value_weighting.receipt.v1"
    assert receipt["weighted_value_usd"] == 12_600.0
    assert receipt["evidence_weight"] == 0.30
    assert receipt["duration_weight"] == 0.70
    assert receipt["attribution_weight"] == 0.60
    assert receipt["payload_hash"].startswith("sha256:")
