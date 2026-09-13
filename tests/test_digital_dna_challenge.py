from pathlib import Path

from digital_dna import ContinuityDecision
from digital_dna.challenge import (
    OracleLabel,
    ExperimentalLineageGuard,
    lineage_guard_factory,
    load_preregistered_challenge,
    run_challenge,
    transition_only_factory,
)


PREREG = (
    Path(__file__).parents[1]
    / "experiments"
    / "preregistrations"
    / "framleis_twin_continuity_v1.json"
)


def challenge():
    return load_preregistered_challenge(PREREG)


def report(factory, name):
    return run_challenge(challenge(), name, factory)


def result(report, step_id):
    return next(item for item in report.results if item.step_id == step_id)


def test_preregistration_is_frozen_and_machine_loadable():
    loaded = challenge()

    assert loaded.challenge_id == "framleis-twin-continuity-v1"
    assert loaded.epistemic_status == "falsification_criterion"
    assert len(loaded.source_digest) == 64
    assert {scenario.family for scenario in loaded.scenarios} == {
        "legitimate_change",
        "acute_compromise",
        "slow_poisoning",
        "fork_clone",
    }


def test_transition_only_baseline_exposes_cumulative_drift_weakness():
    baseline = report(transition_only_factory, "transition-only-v0.1")

    assert result(baseline, "poison-3").oracle is OracleLabel.PLAUSIBLE_BUT_ASK
    assert result(baseline, "poison-3").decision is ContinuityDecision.CONTINUES
    assert result(baseline, "poison-4").oracle is OracleLabel.NOT_ME
    assert result(baseline, "poison-4").decision is ContinuityDecision.CONTINUES
    assert result(baseline, "poison-5").decision is ContinuityDecision.CONTINUES
    assert baseline.detection_delay_steps["slow-poisoning"] is None
    assert baseline.metrics.missed_review >= 1
    assert baseline.metrics.false_continuity >= 2


def test_transition_only_baseline_cannot_detect_noncanonical_fork():
    baseline = report(transition_only_factory, "transition-only-v0.1")

    assert result(baseline, "fork-1").decision is ContinuityDecision.CONTINUES
    assert result(baseline, "fork-2").oracle is OracleLabel.NOT_ME
    assert result(baseline, "fork-2").decision is ContinuityDecision.CONTINUES
    assert baseline.detection_delay_steps["canonical-fork"] is None


def test_existing_rules_detect_acute_principal_hijack():
    baseline = report(transition_only_factory, "transition-only-v0.1")

    acute = result(baseline, "acute-1")
    assert acute.oracle is OracleLabel.NOT_ME
    assert acute.decision is ContinuityDecision.BREAK
    assert any(reason.startswith("invariant_failed:principal.id") for reason in acute.reasons)
    assert baseline.detection_delay_steps["acute-principal-hijack"] == 0


def test_experimental_lineage_guard_detects_review_break_and_fork():
    guarded = report(lineage_guard_factory, "experimental-lineage-guard")

    assert result(guarded, "poison-3").decision is ContinuityDecision.REVIEW_REQUIRED
    assert result(guarded, "poison-4").decision is ContinuityDecision.BREAK
    assert guarded.detection_delay_steps["slow-poisoning"] == 0

    fork = result(guarded, "fork-2")
    assert fork.decision is ContinuityDecision.BREAK
    assert fork.reasons == ("lineage_parent_mismatch",)
    assert guarded.detection_delay_steps["canonical-fork"] == 0


def test_lineage_guard_improves_false_continuity_without_false_breaking_legitimate_trace():
    baseline = report(transition_only_factory, "transition-only-v0.1")
    guarded = report(lineage_guard_factory, "experimental-lineage-guard")

    assert guarded.metrics.false_continuity < baseline.metrics.false_continuity
    assert guarded.metrics.missed_review < baseline.metrics.missed_review
    assert guarded.metrics.false_break == 0

    legitimate = [
        item
        for item in guarded.results
        if item.scenario_id == "legitimate-development"
    ]
    assert legitimate
    assert all(item.decision is ContinuityDecision.CONTINUES for item in legitimate)


def test_lineage_guard_is_research_comparator_not_authority_api():
    assert not hasattr(ExperimentalLineageGuard, "authorize")
    assert not hasattr(ExperimentalLineageGuard, "execute")
