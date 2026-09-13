from datetime import datetime, timezone
from decimal import Decimal

import pytest

from services.organizational_simulation.value_opportunity import (
    OrganizationProfile,
    OrganizationSize,
    ValueSimulationFactory,
    VerticalValueBenchmark,
    EvidenceBasis,
    calibrate_benchmark_from_shadow,
    measure_shadow_value,
)
from services.reht.shadow_harness import CaseFixture, DecisionPath, PathOutcome
from src.valo_platform.action_envelope.value_measurement import MeasurementStatus


def shadow_cases():
    return [
        CaseFixture(
            case_id="unsafe-human-approved",
            proposed_action="publish unverified claim",
            ground_truth_approve=False,
            human_only=PathOutcome.ALLOW,
            ai_only=PathOutcome.ALLOW,
            ai_plus_reht=PathOutcome.DENY,
            time_human_only=300,
            time_ai_only=20,
            time_ai_plus_reht=60,
        ),
        CaseFixture(
            case_id="safe-human-denied",
            proposed_action="send bounded update",
            ground_truth_approve=True,
            human_only=PathOutcome.DENY,
            ai_only=PathOutcome.ALLOW,
            ai_plus_reht=PathOutcome.ALLOW,
            time_human_only=240,
            time_ai_only=15,
            time_ai_plus_reht=50,
        ),
        CaseFixture(
            case_id="safe-approved",
            proposed_action="read public record",
            ground_truth_approve=True,
            human_only=PathOutcome.ALLOW,
            ai_only=PathOutcome.ALLOW,
            ai_plus_reht=PathOutcome.ALLOW,
            time_human_only=180,
            time_ai_only=10,
            time_ai_plus_reht=40,
        ),
        CaseFixture(
            case_id="unsafe-blocked",
            proposed_action="export restricted data",
            ground_truth_approve=False,
            human_only=PathOutcome.DENY,
            ai_only=PathOutcome.ALLOW,
            ai_plus_reht=PathOutcome.HALT,
            time_human_only=360,
            time_ai_only=25,
            time_ai_plus_reht=70,
        ),
    ]


def test_shadow_mode_emits_canonical_before_after_value_deltas():
    deltas = measure_shadow_value(
        cases=shadow_cases(),
        baseline_path=DecisionPath.HUMAN_ONLY,
        comparison_scope="media:NO:large",
        measured_at=datetime(2026, 7, 23, tzinfo=timezone.utc),
    )
    by_id = {delta.metric_id: delta for delta in deltas}

    assert by_id["shadow_false_approval_rate"].improvement_delta == Decimal("0.25")
    assert by_id["shadow_false_denial_rate"].improvement_delta == Decimal("0.25")
    assert by_id["shadow_mean_decision_time"].improvement_delta == Decimal("215")
    assert all(delta.status == MeasurementStatus.IMPROVED for delta in deltas)


def test_shadow_calibration_builds_vertical_benchmark():
    calibration = calibrate_benchmark_from_shadow(
        benchmark_id="media-no-large-v1",
        vertical="media",
        country="NO",
        organization_size=OrganizationSize.LARGE,
        currency="NOK",
        cases=shadow_cases(),
        prevented_loss_per_false_approval="100000",
        recovered_value_per_false_denial="20000",
        labor_cost_per_hour="1000",
        evidence_quality="0.8",
        reference_annual_actions="10000",
        reference_employees=500,
        reference_annual_revenue="1000000000",
        source_refs=["shadow-run:1"],
    )

    benchmark = calibration.benchmark
    assert benchmark.false_approval_reduction_rate == Decimal("0.25")
    assert benchmark.false_denial_reduction_rate == Decimal("0.25")
    assert benchmark.human_minutes_saved_per_action == Decimal(
        "3.583333333333333333333333333"
    )
    assert benchmark.sample_size == 4
    assert benchmark.evidence_basis == EvidenceBasis.SHADOW_CALIBRATED
    assert len(calibration.metric_deltas) == 3


def benchmark(**overrides):
    values = dict(
        benchmark_id="media-no-large",
        vertical="media",
        country="NO",
        organization_size=OrganizationSize.LARGE,
        currency="NOK",
        evidence_basis=EvidenceBasis.SHADOW_CALIBRATED,
        sample_size=100,
        benchmark_confidence=Decimal("0.8"),
        false_approval_reduction_rate=Decimal("0.01"),
        false_denial_reduction_rate=Decimal("0.02"),
        human_minutes_saved_per_action=Decimal("3"),
        prevented_loss_per_false_approval=Decimal("100000"),
        recovered_value_per_false_denial=Decimal("10000"),
        labor_cost_per_hour=Decimal("1000"),
        reference_annual_actions=Decimal("10000"),
        reference_employees=500,
        reference_annual_revenue=Decimal("1000000000"),
    )
    values.update(overrides)
    return VerticalValueBenchmark(**values)


def test_simulation_scales_value_from_observed_action_volume():
    factory = ValueSimulationFactory([benchmark()])
    profile = OrganizationProfile(
        organization_id="org-1",
        name="Publisher",
        vertical="media",
        country="NO",
        employees=600,
        annual_governed_actions=10000,
        annual_revenue=Decimal("1500000000"),
        revenue_currency="NOK",
        ai_adoption=Decimal("0.5"),
        consequence_exposure=Decimal("0.8"),
        governance_gap=Decimal("0.75"),
        data_confidence=Decimal("0.9"),
        contactability=Decimal("0.8"),
    )

    result = factory.simulate_organization(profile)

    assert result.annual_actions_in_scope == Decimal("4000.0")
    assert result.prevented_false_approvals == Decimal("40.00")
    assert result.recovered_false_denials == Decimal("80.00")
    assert result.human_hours_saved == Decimal("200.0")
    assert result.gross_annual_value == Decimal("3750000.000")
    assert result.action_volume_basis == "organization_observed"
    assert result.estimate_confidence == Decimal("0.72")


def test_simulation_infers_action_volume_from_size_and_revenue():
    factory = ValueSimulationFactory([benchmark()])
    profile = OrganizationProfile(
        organization_id="org-2",
        name="Scaled Publisher",
        vertical="media",
        country="NO",
        employees=1000,
        annual_revenue=Decimal("2000000000"),
        revenue_currency="NOK",
    )

    result = factory.simulate_organization(profile)

    assert result.annual_actions_in_scope == Decimal("20000")
    assert result.action_volume_basis == "benchmark_scaled"
    assert result.estimate_confidence == Decimal("0.45")


def test_factory_selects_best_segment_and_ranks_targets():
    global_generic = benchmark(
        benchmark_id="media-global",
        country=None,
        organization_size=None,
        benchmark_confidence=Decimal("0.9"),
    )
    exact = benchmark(
        benchmark_id="media-no-large",
        country="NO",
        organization_size=OrganizationSize.LARGE,
        benchmark_confidence=Decimal("0.7"),
    )
    factory = ValueSimulationFactory([global_generic, exact])

    high = OrganizationProfile(
        organization_id="high",
        name="High Value",
        vertical="media",
        country="NO",
        employees=600,
        annual_governed_actions=20000,
        contactability=Decimal("0.8"),
    )
    low = OrganizationProfile(
        organization_id="low",
        name="Low Value",
        vertical="media",
        country="NO",
        employees=600,
        annual_governed_actions=1000,
        contactability=Decimal("1"),
    )

    assert factory.select_benchmark(high).benchmark_id == "media-no-large"
    ranked = factory.rank_targets([low, high])
    assert [item.organization_id for item in ranked] == ["high", "low"]


def test_unknown_vertical_or_unscalable_volume_fails_closed():
    factory = ValueSimulationFactory([benchmark()])

    with pytest.raises(ValueError, match="no benchmark"):
        factory.simulate_organization(
            OrganizationProfile(
                organization_id="health",
                name="Hospital",
                vertical="healthcare",
                country="NO",
                employees=1000,
                annual_governed_actions=100,
            )
        )

    no_scale = benchmark(
        benchmark_id="no-scale",
        reference_annual_actions=None,
        reference_employees=None,
        reference_annual_revenue=None,
    )
    with pytest.raises(ValueError, match="action volume is unknown"):
        ValueSimulationFactory([no_scale]).simulate_organization(
            OrganizationProfile(
                organization_id="unknown-volume",
                name="Unknown",
                vertical="media",
                country="NO",
                employees=600,
            )
        )
