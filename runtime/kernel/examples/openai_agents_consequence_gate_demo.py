from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from valo_kernel.contracts.common import canonical_digest
from valo_kernel.integrations.openai_agents import (
    ConsequenceDecision,
    GateDisposition,
    OpenAIToolCall,
    evaluate_tool_call,
)


NOW = datetime(2026, 9, 3, 9, 30, tzinfo=UTC)


async def main() -> None:
    revoked = False

    def consequence_authorizer(call: OpenAIToolCall) -> ConsequenceDecision:
        if revoked:
            return ConsequenceDecision(
                disposition=GateDisposition.DENY,
                decision_ref="reht:racs:demo:revoked",
                evaluated_at=NOW,
                request_digest=call.request_digest,
                reason="authority revoked before consequence",
            )

        return ConsequenceDecision(
            disposition=GateDisposition.ALLOW,
            decision_ref="reht:racs:demo:allow",
            evaluated_at=NOW,
            valid_until=NOW + timedelta(seconds=5),
            request_digest=call.request_digest,
            action_digest=canonical_digest(
                {
                    "capability": "send_payment",
                    "target": "supplier:42",
                    "amount": 100,
                    "currency": "EUR",
                }
            ),
        )

    before_revocation = await evaluate_tool_call(
        tool_name="send_payment",
        tool_call_id="call_before",
        raw_arguments='{"supplier":"42","amount":100,"currency":"EUR"}',
        authorizer=consequence_authorizer,
        now=NOW,
        clock=lambda: NOW,
    )

    revoked = True
    after_revocation = await evaluate_tool_call(
        tool_name="send_payment",
        tool_call_id="call_after",
        raw_arguments='{"supplier":"42","amount":100,"currency":"EUR"}',
        authorizer=consequence_authorizer,
        now=NOW,
        clock=lambda: NOW,
    )

    print(
        {
            "before_revocation": before_revocation.disposition.value,
            "before_tool_effect": before_revocation.allowed,
            "after_revocation": after_revocation.disposition.value,
            "after_tool_effect": after_revocation.allowed,
            "boundary": "OpenAI FunctionTool input guardrail / consequence time",
        }
    )


if __name__ == "__main__":
    asyncio.run(main())
