from datetime import UTC, datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from local_runtime import ConsequenceDenied, LocalRuntime


NOW = datetime(2026, 9, 19, tzinfo=UTC)


def influenced_action(**overrides):
    action = {
        "type": "purchase",
        "actor_id": "agent-1",
        "target": "merchant-1",
        "payload": {"sku": "item-1", "amount": 100, "currency": "EUR"},
        "principal_intent_before_influence": "buy-best-value",
        "agent_recommendation": "buy-item-1",
        "principal_decision_after_influence": "buy-item-1",
    }
    action.update(overrides)
    return action


def test_disagreement_or_persuasion_remains_permitted():
    runtime = LocalRuntime()
    aid = runtime.submit(
        influenced_action(
            agent_recommendation="do-not-buy-original-choice",
            influence_mode="disagreement-and-persuasion",
        )
    )

    assert runtime.result(aid).status == "FAILURE"
    assert "ACTION_REQUESTED" in [event.kind for event in runtime.stream(aid)]


def test_post_influence_decision_with_explicit_fresh_grant_can_authorize():
    runtime = LocalRuntime()
    aid = runtime.submit(influenced_action())

    runtime.grant(aid)
    permit = runtime.authorize(aid, now=NOW)

    assert permit.action_id == aid
    assert permit.authority_revision >= 2


def test_persuasion_alone_does_not_confer_effect_authority():
    runtime = LocalRuntime()
    aid = runtime.submit(influenced_action(influence_mode="persuasion"))

    with pytest.raises(ConsequenceDenied, match="authority denied"):
        runtime.authorize(aid, now=NOW)


def test_preference_change_alone_does_not_confer_effect_authority():
    runtime = LocalRuntime()
    aid = runtime.submit(
        influenced_action(
            principal_intent_before_influence="do-not-buy",
            principal_decision_after_influence="buy-item-1",
            preference_changed=True,
        )
    )

    with pytest.raises(ConsequenceDenied, match="authority denied"):
        runtime.authorize(aid, now=NOW)


def test_agent_objective_does_not_substitute_principal_authority():
    runtime = LocalRuntime()
    aid = runtime.submit(
        influenced_action(
            agent_optimization_objective="maximize-partner-sales",
            objective_conflicts_with_principal=True,
        )
    )

    with pytest.raises(ConsequenceDenied, match="authority denied"):
        runtime.authorize(aid, now=NOW)
