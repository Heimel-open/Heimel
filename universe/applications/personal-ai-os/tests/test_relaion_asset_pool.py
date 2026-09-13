from paios.relaion_asset_pool import (
    AssetProfile,
    ReservedWindow,
    RiskQuote,
    ServiceRequirement,
    build_pool_offer,
    propose_pool_allocation,
)


def test_cottage_pool_offer_prices_unused_capacity_and_preserves_owner_rights():
    asset = AssetProfile(
        asset_id="cottage-1",
        owner_id="person-1",
        kind="cottage",
        location="Norway",
        annual_cost=180_000,
        estimated_value=4_000_000,
        used_days_last_year=14,
        owner_reserved=(ReservedWindow("2027-03-20", "2027-03-28", "easter"),),
        emotional_value=0.9,
    )
    services = (
        ServiceRequirement("turnover_cleaning", "ready_before_next_guest", 900),
    )
    risks = (
        RiskQuote.price(
            risk="guest_damage",
            exposure=100_000,
            probability=0.01,
            loading=1.5,
            underwriter="demo-underwriter",
        ),
    )

    offer = build_pool_offer(
        asset,
        owner_days_reserved=30,
        expected_daily_revenue=2_500,
        expected_occupancy=0.20,
        services=services,
        risks=risks,
    )

    assert offer.available_days == 335
    assert asset.cost_per_used_day == 180_000 / 14
    assert offer.expected_gross_yield == 167_500
    assert offer.expected_service_cost == 60_300
    assert offer.expected_risk_premium == 1_500
    assert offer.expected_net_yield == 105_700

    envelope = propose_pool_allocation(
        offer,
        actor_id="relaion-1",
        mandate_id="mandate-1",
        policy_id="asset-pool-v1",
    )

    assert envelope.action_type == "ASSET_POOL_ALLOCATE"
    assert envelope.requested_effect["preserve_owner_title"] is True
    assert envelope.requested_effect["requires_fresh_match_before_access"] is True
    assert "grant_access" in envelope.authority_context["excludes"]
    assert "charge" in envelope.authority_context["excludes"]
    assert envelope.risk_context["must_be_bound_at_consequence_time"] is True


def test_risk_quote_rejects_invalid_probability():
    try:
        RiskQuote.price(
            risk="damage",
            exposure=1_000,
            probability=1.1,
            loading=1.2,
            underwriter="x",
        )
    except ValueError as exc:
        assert "probability" in str(exc)
    else:
        raise AssertionError("invalid probability must fail closed")
