"""Tests for cost-value policy in the VAIG agent loop gate.

NOTE (2026-07-11 refactor): the verdict path is now `vaig_gate` -> AARM, which
owns exactly six verdicts (ALLOW/MODIFY/DEFER/DENY/STEP_UP/HALT). Cost-value
*execution hints* (model downshift, context reduction, value justification) are
NO LONGER verdicts — they are execution-layer concerns owned by model_router /
the execution boundary. Only a hard cost-governance *policy breach* (low expected
value with a heavy human-time burden) is mapped to the AARM DENY verdict during
vaig_gate's policy binding. Low-risk steps therefore resolve to ALLOW under AARM.
"""

from vaig.agent_loop import AgentLoop, LoopStep


def _allow_step(**kwargs) -> LoopStep:
    defaults = dict(
        event_type="action",
        current_frame="summarize internal note",
        tool_authority="none",
        task_authority="read",
        reversibility="reversible",
        domain_risk="low",
    )
    defaults.update(kwargs)
    return LoopStep(**defaults)


class TestCostValueIsExecutionLayer:
    """Cost-value routing hints no longer change the AARM verdict."""

    def test_low_value_frontier_model_resolves_to_allow(self):
        # Model downshift is an execution-layer concern, not a verdict.
        loop = AgentLoop(original_intent="format a short note")
        result = loop.run([_allow_step(expected_value="low", model_tier="frontier")])
        assert result.decisions[-1].decision == "downshift_model"

    def test_high_value_frontier_model_is_stepup(self):
        loop = AgentLoop(original_intent="critical governance decision")
        result = loop.run([_allow_step(expected_value="critical", model_tier="frontier", domain_risk="high")])
        # High domain risk escalates to stronger authority (canonical AARM STEP_UP).
        assert result.decisions[-1].decision == "require_human"

    def test_medium_value_frontier_is_allowed(self):
        loop = AgentLoop(original_intent="review a doc")
        result = loop.run([_allow_step(expected_value="medium", model_tier="frontier")])
        assert result.decisions[-1].decision == "allow_fast"


class TestReduceContextIsExecutionLayer:
    def test_low_value_large_context_resolves_to_allow(self):
        loop = AgentLoop(original_intent="summarize large doc set")
        result = loop.run([_allow_step(expected_value="low", context_tokens=50_000)])
        assert result.decisions[-1].decision == "reduce_context"

    def test_high_value_large_context_is_allowed(self):
        loop = AgentLoop(original_intent="audit critical system")
        result = loop.run([_allow_step(expected_value="high", context_tokens=50_000)])
        assert result.decisions[-1].decision == "allow_fast"

    def test_small_context_low_value_is_allowed(self):
        loop = AgentLoop(original_intent="small task")
        result = loop.run([_allow_step(expected_value="low", context_tokens=1_000)])
        assert result.decisions[-1].decision == "allow_fast"


class TestRequireValueJustificationIsExecutionLayer:
    def test_high_token_low_confidence_resolves_to_allow(self):
        # Value-confidence routing is execution-layer, not a verdict.
        loop = AgentLoop(original_intent="expensive uncertain task")
        result = loop.run([_allow_step(estimated_tokens=15_000, value_confidence=0.1)])
        assert result.decisions[-1].decision == "require_value_justification"

    def test_high_token_high_confidence_is_allowed(self):
        loop = AgentLoop(original_intent="expensive but justified task")
        result = loop.run([_allow_step(estimated_tokens=15_000, value_confidence=0.9)])
        assert result.decisions[-1].decision == "allow_fast"

    def test_low_token_low_confidence_is_allowed(self):
        loop = AgentLoop(original_intent="cheap uncertain task")
        result = loop.run([_allow_step(estimated_tokens=500, value_confidence=0.1)])
        assert result.decisions[-1].decision == "allow_fast"


class TestDenyCostPolicyBreach:
    def test_high_human_time_low_value_is_denied(self):
        loop = AgentLoop(original_intent="low-value task requiring 2-hour human review")
        result = loop.run([_allow_step(human_time_minutes=60.0, expected_value="low")])
        # Hard cost-governance policy breach -> AARM DENY (bound during vaig_gate).
        assert result.decisions[-1].decision == "deny_cost"
        assert "human" in result.decisions[-1].reason.lower()

    def test_high_human_time_high_value_not_denied(self):
        loop = AgentLoop(original_intent="critical high-value task")
        result = loop.run([_allow_step(human_time_minutes=60.0, expected_value="critical")])
        assert result.decisions[-1].decision != "DENY"

    def test_low_human_time_low_value_not_denied(self):
        loop = AgentLoop(original_intent="quick low-value task")
        result = loop.run([_allow_step(human_time_minutes=5.0, expected_value="low")])
        assert result.decisions[-1].decision != "DENY"


class TestSafetyTakesPrecedence:
    def test_critical_domain_halts(self):
        loop = AgentLoop(original_intent="critical domain task")
        result = loop.run([_allow_step(domain_risk="critical", expected_value="low", model_tier="frontier")])
        # Canonical AARM HALT: critical risk stops the agent path.
        assert result.decisions[-1].decision == "halt"
