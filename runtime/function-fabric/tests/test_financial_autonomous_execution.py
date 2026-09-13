from decimal import Decimal

from valo_function_fabric.packs.financial_autonomous_execution import (
    CapitalAuthorityEnvelope,
    FinancialExecutionIntent,
    LiveRiskState,
    evaluate_financial_constraints,
)


def envelope() -> CapitalAuthorityEnvelope:
    return CapitalAuthorityEnvelope(
        allowed_instruments=frozenset({"BTC-USD", "ETH-USD"}),
        allowed_venues=frozenset({"venue-a"}),
        max_order_notional=Decimal(100000),
        max_position_notional=Decimal(250000),
        max_gross_exposure=Decimal(500000),
        max_leverage=Decimal("2.0"),
        max_concentration=Decimal("0.25"),
        max_daily_loss=Decimal(10000),
        max_drawdown=Decimal("0.08"),
    )


def intent(**overrides: object) -> FinancialExecutionIntent:
    values: dict[str, object] = {
        "instrument": "BTC-USD",
        "venue": "venue-a",
        "order_notional": Decimal(50000),
        "projected_position_notional": Decimal(150000),
        "projected_gross_exposure": Decimal(300000),
        "projected_leverage": Decimal("1.5"),
        "projected_concentration": Decimal("0.20"),
        "portfolio_version": "v42",
        "purpose": "delta-neutral alpha execution",
    }
    values.update(overrides)
    return FinancialExecutionIntent(**values)  # type: ignore[arg-type]


def test_candidate_inside_envelope_is_admissible_but_not_authorized() -> None:
    result = evaluate_financial_constraints(
        intent(),
        envelope(),
        LiveRiskState(portfolio_version="v42", daily_pnl=Decimal(1250), drawdown=Decimal("0.02")),
    )

    assert result.admissible is True
    assert result.violations == ()


def test_stale_portfolio_state_fails_closed() -> None:
    result = evaluate_financial_constraints(
        intent(portfolio_version="v41"),
        envelope(),
        LiveRiskState(portfolio_version="v42", daily_pnl=Decimal(0), drawdown=Decimal("0.01")),
    )

    assert result.admissible is False
    assert "STALE_PORTFOLIO_STATE" in result.violations


def test_live_loss_and_drawdown_stop_new_action() -> None:
    result = evaluate_financial_constraints(
        intent(),
        envelope(),
        LiveRiskState(portfolio_version="v42", daily_pnl=Decimal(-10001), drawdown=Decimal("0.081")),
    )

    assert result.admissible is False
    assert "DAILY_LOSS_LIMIT" in result.violations
    assert "DRAWDOWN_LIMIT" in result.violations


def test_projected_capital_limits_fail_closed() -> None:
    result = evaluate_financial_constraints(
        intent(
            order_notional=Decimal(100001),
            projected_position_notional=Decimal(250001),
            projected_gross_exposure=Decimal(500001),
            projected_leverage=Decimal("2.1"),
            projected_concentration=Decimal("0.30"),
        ),
        envelope(),
        LiveRiskState(portfolio_version="v42", daily_pnl=Decimal(0), drawdown=Decimal("0.01")),
    )

    assert set(result.violations) >= {
        "ORDER_NOTIONAL_LIMIT",
        "POSITION_NOTIONAL_LIMIT",
        "GROSS_EXPOSURE_LIMIT",
        "LEVERAGE_LIMIT",
        "CONCENTRATION_LIMIT",
    }


def test_execution_boundary_and_receipt_requirements_cannot_be_disabled() -> None:
    result = evaluate_financial_constraints(
        intent(requires_reht=False, requires_external_effect_verification=False),
        envelope(),
        LiveRiskState(portfolio_version="v42", daily_pnl=Decimal(0), drawdown=Decimal("0.01")),
    )

    assert result.admissible is False
    assert "REHT_REQUIRED" in result.violations
    assert "EXTERNAL_EFFECT_VERIFICATION_REQUIRED" in result.violations


def test_out_of_scope_instrument_and_venue_are_denied() -> None:
    result = evaluate_financial_constraints(
        intent(instrument="DOGE-USD", venue="venue-b"),
        envelope(),
        LiveRiskState(portfolio_version="v42", daily_pnl=Decimal(0), drawdown=Decimal("0.01")),
    )

    assert result.admissible is False
    assert "INSTRUMENT_OUT_OF_SCOPE" in result.violations
    assert "VENUE_OUT_OF_SCOPE" in result.violations
