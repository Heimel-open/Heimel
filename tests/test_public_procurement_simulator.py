from decimal import Decimal

import pytest
from pydantic import ValidationError

from valo_platform.public_procurement.simulator import (
    ProcurementGovernanceMode,
    ProcurementScenario,
    ProcurementScenarioKind,
    SimulationDecision,
    aggregate_catalogue_metrics,
    compare_governance_modes,
    default_procurement_scenarios,
    run_procurement_catalogue,
    run_procurement_scenario,
)


def by_mode(comparison):
    return {outcome.mode: outcome for outcome in comparison.outcomes}


def test_catalogue_contains_required_deterministic_scenarios() -> None:
    scenarios = default_procurement_scenarios()

    assert len(scenarios) == 11
    assert len({scenario.scenario_id for scenario in scenarios}) == 11
    assert {scenario.kind for scenario in scenarios} == set(ProcurementScenarioKind)


def test_comparison_uses_identical_input_digest_for_all_modes() -> None:
    comparison = compare_governance_modes(default_procurement_scenarios()[0])

    assert len({outcome.scenario_digest for outcome in comparison.outcomes}) == 1
    assert {outcome.mode for outcome in comparison.outcomes} == set(ProcurementGovernanceMode)


def test_simulation_is_repeatable_without_randomness() -> None:
    scenario = default_procurement_scenarios()[6]

    first = run_procurement_scenario(scenario, ProcurementGovernanceMode.EMOS_ACE)
    second = run_procurement_scenario(scenario, ProcurementGovernanceMode.EMOS_ACE)

    assert first == second


def test_bank_change_exposes_difference_between_modes() -> None:
    scenario = next(
        item
        for item in default_procurement_scenarios()
        if item.kind is ProcurementScenarioKind.SUPPLIER_BANK_CHANGE
    )
    outcomes = by_mode(compare_governance_modes(scenario))

    unrestricted = outcomes[ProcurementGovernanceMode.UNRESTRICTED]
    classic = outcomes[ProcurementGovernanceMode.CLASSIC_CONTROLS]
    emos = outcomes[ProcurementGovernanceMode.EMOS_ACE]

    assert unrestricted.realized_loss_nok == Decimal("2500000.00")
    assert classic.realized_loss_nok == Decimal("2500000.00")
    assert emos.decision is SimulationDecision.STEP_UP
    assert emos.prevented_loss_nok == Decimal("2500000.00")
    assert emos.ace_minutes == 20


def test_classic_static_control_catches_weighting_rule() -> None:
    scenario = next(
        item
        for item in default_procurement_scenarios()
        if item.kind is ProcurementScenarioKind.LABOUR_INTENSIVE_WEIGHTING
    )

    outcome = run_procurement_scenario(
        scenario,
        ProcurementGovernanceMode.CLASSIC_CONTROLS,
    )

    assert outcome.decision is SimulationDecision.DEFER
    assert outcome.safe_outcome is True


def test_catalogue_metrics_measure_ace_cost_and_prevented_loss() -> None:
    metrics = {
        item.mode: item
        for item in aggregate_catalogue_metrics(run_procurement_catalogue())
    }

    unrestricted = metrics[ProcurementGovernanceMode.UNRESTRICTED]
    classic = metrics[ProcurementGovernanceMode.CLASSIC_CONTROLS]
    emos = metrics[ProcurementGovernanceMode.EMOS_ACE]

    assert unrestricted.realized_loss_nok == Decimal("12000000.00")
    assert classic.realized_loss_nok == Decimal("7250000.00")
    assert emos.realized_loss_nok == Decimal("0.00")
    assert emos.prevented_loss_nok == Decimal("12000000.00")
    assert emos.total_ace_minutes == 250
    assert emos.safe_outcomes == 11
    assert emos.average_outcome_quality > classic.average_outcome_quality


def test_scenario_cannot_be_used_to_grant_authority() -> None:
    with pytest.raises(ValidationError, match="cannot grant authority"):
        ProcurementScenario(
            scenario_id="invalid",
            kind=ProcurementScenarioKind.PRICE_ONLY_AWARD,
            title="Invalid authority scenario",
            proposed_action="Commit award",
            loss_exposure_nok=Decimal("1.00"),
            safe_to_commit_without_step_up=False,
            requires_human_step_up=True,
            classic_control_detects=False,
            governance_steps_classic=1,
            governance_steps_emos=1,
            classic_delay_hours=Decimal("1.00"),
            emos_delay_hours=Decimal("1.00"),
            ace_minutes=1,
            grants_authority=True,
        )
