from __future__ import annotations

import asyncio
import sys
import types
from datetime import UTC, datetime, timedelta

from valo_kernel.contracts.common import canonical_digest
from valo_kernel.integrations.openai_agents import (
    ConsequenceDecision,
    GateDisposition,
    OpenAIToolCall,
    evaluate_tool_call,
    make_openai_tool_input_guardrail,
)


NOW = datetime(2026, 9, 3, 9, 30, tzinfo=UTC)
ACTION_DIGEST = canonical_digest({"action": "send_payment", "amount": 100})


def run(coro):
    return asyncio.run(coro)


def allow(call: OpenAIToolCall) -> ConsequenceDecision:
    return ConsequenceDecision(
        disposition=GateDisposition.ALLOW,
        decision_ref="reht:racs:allow:1",
        evaluated_at=NOW,
        valid_until=NOW + timedelta(seconds=5),
        request_digest=call.request_digest,
        action_digest=ACTION_DIGEST,
    )


def test_fresh_exact_allow_passes() -> None:
    result = run(
        evaluate_tool_call(
            tool_name="send_payment",
            tool_call_id="call_1",
            raw_arguments='{"amount":100,"currency":"EUR"}',
            authorizer=allow,
            now=NOW,
            clock=lambda: NOW,
        )
    )

    assert result.allowed is True
    assert result.disposition == GateDisposition.ALLOW
    assert result.action_digest == ACTION_DIGEST


def test_deny_produces_zero_clearance() -> None:
    def deny(call: OpenAIToolCall) -> ConsequenceDecision:
        return ConsequenceDecision(
            disposition=GateDisposition.DENY,
            decision_ref="reht:racs:deny:1",
            evaluated_at=NOW,
            request_digest=call.request_digest,
            reason="revoked mandate",
        )

    result = run(
        evaluate_tool_call(
            tool_name="send_payment",
            tool_call_id="call_2",
            raw_arguments='{"amount":100}',
            authorizer=deny,
            now=NOW,
            clock=lambda: NOW,
        )
    )

    assert result.allowed is False
    assert result.disposition == GateDisposition.DENY
    assert result.reason == "revoked mandate"


def test_escalate_is_not_execution_clearance() -> None:
    def escalate(call: OpenAIToolCall) -> ConsequenceDecision:
        return ConsequenceDecision(
            disposition=GateDisposition.ESCALATE,
            decision_ref="reht:racs:escalate:1",
            evaluated_at=NOW,
            request_digest=call.request_digest,
            reason="human approval required",
        )

    result = run(
        evaluate_tool_call(
            tool_name="wire_transfer",
            tool_call_id="call_3",
            raw_arguments='{"amount":50000}',
            authorizer=escalate,
            now=NOW,
            clock=lambda: NOW,
        )
    )

    assert result.allowed is False
    assert result.disposition == GateDisposition.ESCALATE


def test_malformed_arguments_fail_closed_without_authorizer_call() -> None:
    calls = 0

    def must_not_run(call: OpenAIToolCall) -> ConsequenceDecision:
        nonlocal calls
        calls += 1
        return allow(call)

    result = run(
        evaluate_tool_call(
            tool_name="send_payment",
            tool_call_id="call_4",
            raw_arguments="not-json",
            authorizer=must_not_run,
            now=NOW,
            clock=lambda: NOW,
        )
    )

    assert result.allowed is False
    assert result.disposition == GateDisposition.DENY
    assert calls == 0


def test_decision_bound_to_other_call_fails_closed() -> None:
    def drifted(_: OpenAIToolCall) -> ConsequenceDecision:
        return ConsequenceDecision(
            disposition=GateDisposition.ALLOW,
            decision_ref="reht:racs:allow:drifted",
            evaluated_at=NOW,
            valid_until=NOW + timedelta(seconds=5),
            request_digest="0" * 64,
            action_digest=ACTION_DIGEST,
        )

    result = run(
        evaluate_tool_call(
            tool_name="send_payment",
            tool_call_id="call_5",
            raw_arguments='{"amount":101}',
            authorizer=drifted,
            now=NOW,
            clock=lambda: NOW,
        )
    )

    assert result.allowed is False
    assert result.disposition == GateDisposition.DENY
    assert "another tool call" in result.reason


def test_stale_allow_fails_closed_at_effect_boundary() -> None:
    def stale(call: OpenAIToolCall) -> ConsequenceDecision:
        return ConsequenceDecision(
            disposition=GateDisposition.ALLOW,
            decision_ref="reht:racs:allow:stale",
            evaluated_at=NOW,
            valid_until=NOW + timedelta(seconds=5),
            request_digest=call.request_digest,
            action_digest=ACTION_DIGEST,
        )

    result = run(
        evaluate_tool_call(
            tool_name="send_payment",
            tool_call_id="call_6",
            raw_arguments='{"amount":100}',
            authorizer=stale,
            now=NOW,
            clock=lambda: NOW + timedelta(seconds=6),
        )
    )

    assert result.allowed is False
    assert result.reason == "consequence-time authority clearance is stale"


def test_predated_decision_fails_closed() -> None:
    def predated(call: OpenAIToolCall) -> ConsequenceDecision:
        return ConsequenceDecision(
            disposition=GateDisposition.ALLOW,
            decision_ref="reht:racs:allow:predated",
            evaluated_at=NOW - timedelta(milliseconds=1),
            valid_until=NOW + timedelta(seconds=5),
            request_digest=call.request_digest,
            action_digest=ACTION_DIGEST,
        )

    result = run(
        evaluate_tool_call(
            tool_name="send_payment",
            tool_call_id="call_predated",
            raw_arguments='{"amount":100}',
            authorizer=predated,
            now=NOW,
            clock=lambda: NOW,
        )
    )

    assert result.allowed is False
    assert "predates" in result.reason


def test_argument_reordering_has_same_semantics_but_call_identity_stays_bound() -> None:
    seen: list[str] = []

    def capture(call: OpenAIToolCall) -> ConsequenceDecision:
        seen.append(call.request_digest)
        return allow(call)

    first = run(
        evaluate_tool_call(
            tool_name="send_payment",
            tool_call_id="call_same",
            raw_arguments='{"amount":100,"currency":"EUR"}',
            authorizer=capture,
            now=NOW,
            clock=lambda: NOW,
        )
    )
    second = run(
        evaluate_tool_call(
            tool_name="send_payment",
            tool_call_id="call_same",
            raw_arguments='{"currency":"EUR","amount":100}',
            authorizer=capture,
            now=NOW,
            clock=lambda: NOW,
        )
    )

    assert first.allowed and second.allowed
    assert seen[0] == seen[1]


def test_openai_guardrail_maps_allow_and_deny_to_sdk_behavior(monkeypatch) -> None:
    fake_agents = types.ModuleType("agents")

    class FakeOutput:
        @classmethod
        def allow(cls, output_info=None):
            return {"behavior": "allow", "output_info": output_info}

        @classmethod
        def raise_exception(cls, output_info=None):
            return {"behavior": "raise_exception", "output_info": output_info}

    class FakeGuardrail:
        def __init__(self, *, guardrail_function, name):
            self.guardrail_function = guardrail_function
            self.name = name

    fake_agents.ToolGuardrailFunctionOutput = FakeOutput
    fake_agents.ToolInputGuardrail = FakeGuardrail
    monkeypatch.setitem(sys.modules, "agents", fake_agents)

    gate = make_openai_tool_input_guardrail(allow, clock=lambda: NOW)
    context = types.SimpleNamespace(
        tool_name="send_payment",
        tool_call_id="call_sdk_allow",
        tool_arguments='{"amount":100}',
    )
    allowed = run(gate.guardrail_function(types.SimpleNamespace(context=context)))
    assert allowed["behavior"] == "allow"
    assert allowed["output_info"]["disposition"] == "ALLOW"

    def deny(call: OpenAIToolCall) -> ConsequenceDecision:
        return ConsequenceDecision(
            disposition=GateDisposition.DENY,
            decision_ref="reht:racs:deny:sdk",
            evaluated_at=NOW,
            request_digest=call.request_digest,
            reason="not authorized",
        )

    gate = make_openai_tool_input_guardrail(deny, clock=lambda: NOW)
    denied = run(gate.guardrail_function(types.SimpleNamespace(context=context)))
    assert denied["behavior"] == "raise_exception"
    assert denied["output_info"]["disposition"] == "DENY"
