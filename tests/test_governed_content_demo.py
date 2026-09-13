from __future__ import annotations

from datetime import datetime, timezone

from src.valo_platform.action_envelope.models import ActionDecision
from src.valo_platform.content_operations import build_governed_content_demo


def scenario_map(report):
    return {scenario.scenario_id: scenario for scenario in report.scenarios}


def test_demo_covers_all_required_scenarios_with_expected_outcomes() -> None:
    at = datetime(2026, 7, 31, 19, 0, tzinfo=timezone.utc)
    report = build_governed_content_demo(at)
    scenarios = scenario_map(report)

    assert set(scenarios) == {
        "low-risk-seo-metadata",
        "high-risk-safety-claim",
        "stale-sanity-revision",
        "missing-provenance",
        "unauthorized-publisher",
        "cross-language-semantic-drift",
        "aggregate-batch-escalation",
        "policy-change-invalidation",
    }
    assert scenarios["low-risk-seo-metadata"].batch_decision is ActionDecision.ALLOW
    assert scenarios["high-risk-safety-claim"].batch_decision is ActionDecision.STEP_UP
    assert scenarios["stale-sanity-revision"].batch_decision is ActionDecision.DEFER
    assert scenarios["stale-sanity-revision"].connector_blocked
    assert scenarios["missing-provenance"].batch_decision is ActionDecision.DEFER
    assert scenarios["unauthorized-publisher"].batch_decision is ActionDecision.DENY
    assert (
        scenarios["cross-language-semantic-drift"].batch_decision
        is ActionDecision.STEP_UP
    )
    assert (
        scenarios["aggregate-batch-escalation"].item_decisions
        == (ActionDecision.ALLOW, ActionDecision.ALLOW)
    )
    assert (
        scenarios["aggregate-batch-escalation"].batch_decision
        is ActionDecision.STEP_UP
    )
    assert (
        scenarios["policy-change-invalidation"].batch_decision
        is ActionDecision.DEFER
    )
    assert not scenarios["policy-change-invalidation"].binding_valid
    assert scenarios["policy-change-invalidation"].invalidated_fields == (
        "policy_digest",
    )


def test_demo_is_deterministic_reference_only_and_shadow_mode() -> None:
    at = datetime(2026, 7, 31, 19, 0, tzinfo=timezone.utc)
    first = build_governed_content_demo(at)
    second = build_governed_content_demo(at)

    assert first == second
    assert first.digest() == second.digest()
    assert first.mode == "shadow"
    assert first.content_system == "sanity"
    assert first.production_writes == 0
    assert first.network_calls == 0
    assert not first.live_credentials_used
    assert all(scenario.production_writes == 0 for scenario in first.scenarios)
    assert all(not scenario.execution_authorized for scenario in first.scenarios)


def test_demo_report_contains_no_raw_content_secrets_or_credentials() -> None:
    report_json = build_governed_content_demo().model_dump_json()

    for forbidden in (
        "raw_content",
        "api_key",
        "access_token",
        "client_secret",
        "password",
        "ExecutionReceipt",
        "commit_envelope",
    ):
        assert forbidden not in report_json


def test_completed_workflow_scenarios_have_evidence_chains() -> None:
    scenarios = scenario_map(build_governed_content_demo())
    completed = {
        key: value
        for key, value in scenarios.items()
        if key != "stale-sanity-revision"
    }
    assert all(
        scenario.evidence_chain_digest is not None
        and scenario.evidence_chain_digest.startswith("sha256:")
        for scenario in completed.values()
    )
    assert scenarios["stale-sanity-revision"].evidence_chain_digest is None
