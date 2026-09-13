from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class CapitalAuthorityEnvelope:
    """Deterministic financial limits surrounding an autonomous candidate action.

    This is not an authorization decision. It only constrains the candidate
    action before REHT performs the final execution-time authority check.
    """

    allowed_instruments: frozenset[str]
    allowed_venues: frozenset[str]
    max_order_notional: Decimal
    max_position_notional: Decimal
    max_gross_exposure: Decimal
    max_leverage: Decimal
    max_concentration: Decimal
    max_daily_loss: Decimal
    max_drawdown: Decimal


@dataclass(frozen=True)
class FinancialExecutionIntent:
    instrument: str
    venue: str
    order_notional: Decimal
    projected_position_notional: Decimal
    projected_gross_exposure: Decimal
    projected_leverage: Decimal
    projected_concentration: Decimal
    portfolio_version: str
    purpose: str
    requires_reht: bool = True
    requires_external_effect_verification: bool = True


@dataclass(frozen=True)
class LiveRiskState:
    portfolio_version: str
    daily_pnl: Decimal
    drawdown: Decimal


@dataclass(frozen=True)
class FinancialConstraintResult:
    admissible: bool
    violations: tuple[str, ...]


def evaluate_financial_constraints(
    intent: FinancialExecutionIntent,
    envelope: CapitalAuthorityEnvelope,
    live_state: LiveRiskState,
) -> FinancialConstraintResult:
    """Fail closed when a candidate action exceeds its capital/risk envelope.

    A passing result means only that the candidate remains inside deterministic
    financial constraints. Execution still requires REHT at the boundary and
    external effect verification after the venue call.
    """

    violations: list[str] = []

    if not intent.requires_reht:
        violations.append("REHT_REQUIRED")
    if not intent.requires_external_effect_verification:
        violations.append("EXTERNAL_EFFECT_VERIFICATION_REQUIRED")
    if not intent.purpose.strip():
        violations.append("PURPOSE_REQUIRED")
    if intent.portfolio_version != live_state.portfolio_version:
        violations.append("STALE_PORTFOLIO_STATE")
    if intent.instrument not in envelope.allowed_instruments:
        violations.append("INSTRUMENT_OUT_OF_SCOPE")
    if intent.venue not in envelope.allowed_venues:
        violations.append("VENUE_OUT_OF_SCOPE")
    if intent.order_notional < 0 or intent.order_notional > envelope.max_order_notional:
        violations.append("ORDER_NOTIONAL_LIMIT")
    if intent.projected_position_notional < 0 or intent.projected_position_notional > envelope.max_position_notional:
        violations.append("POSITION_NOTIONAL_LIMIT")
    if intent.projected_gross_exposure < 0 or intent.projected_gross_exposure > envelope.max_gross_exposure:
        violations.append("GROSS_EXPOSURE_LIMIT")
    if intent.projected_leverage < 0 or intent.projected_leverage > envelope.max_leverage:
        violations.append("LEVERAGE_LIMIT")
    if intent.projected_concentration < 0 or intent.projected_concentration > envelope.max_concentration:
        violations.append("CONCENTRATION_LIMIT")
    if live_state.daily_pnl < -envelope.max_daily_loss:
        violations.append("DAILY_LOSS_LIMIT")
    if live_state.drawdown < 0 or live_state.drawdown > envelope.max_drawdown:
        violations.append("DRAWDOWN_LIMIT")

    return FinancialConstraintResult(admissible=not violations, violations=tuple(violations))
