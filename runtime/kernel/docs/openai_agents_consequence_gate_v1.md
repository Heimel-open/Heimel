# OpenAI Agents SDK consequence-time gate v1

## Purpose

This integration places VALO consequence-time admissibility at the OpenAI Agents SDK function-tool execution boundary.

OpenAI tool input guardrails execute immediately before a custom `FunctionTool` is invoked. VALO uses that hook only as an enforcement point. OpenAI does not become the authority source and the adapter cannot mint, widen or reinterpret authority.

```text
agent proposes function tool call
  -> OpenAI ToolContext(tool_name, tool_call_id, tool_arguments)
  -> canonical OpenAIToolCall
  -> VALO consequence authorizer
       -> fresh authority / revocation state
       -> REHT exact-action authorization
       -> RACS disposition
  -> ConsequenceDecision
       ALLOW + fresh exact binding -> effect-time freshness check
                                   -> guardrail allow -> tool executes
       anything else               -> guardrail tripwire -> zero tool effect
```

## Exact-call binding

`OpenAIToolCall` binds:

- resolved tool name
- OpenAI tool call id
- parsed JSON arguments
- consequence-time request timestamp

The canonical digest is supplied to the VALO authorizer. An ALLOW decision is accepted only when it returns the same request digest, an exact governed action digest and a still-valid freshness window.

Changing the tool, arguments, call identity or consequence-time request creates a different digest. Reusing a decision for another call therefore fails closed.

## Time semantics

The request is sealed before authorization. The returned authority decision must be evaluated at or after that request. Immediately after authorization returns, the gate reads the effect-boundary clock again and verifies that the clearance remains inside its validity window.

This prevents both reuse of a decision that predates the actual tool call and expiry during the authorization interval.

## Fail-closed behavior

The gate denies execution when:

- tool arguments are malformed or are not a JSON object
- the authorizer returns DENY, ESCALATE or DEFER
- the decision is bound to another request digest
- the decision predates the consequence-time request
- the effect-boundary clock predates the authority evaluation
- an ALLOW has expired before the tool effect boundary
- ALLOW lacks an exact action digest or positive validity window

The OpenAI adapter maps every non-ALLOW result to `ToolGuardrailFunctionOutput.raise_exception`, preventing the wrapped function tool from executing.

## Dependency boundary

`valo-kernel` does not take a mandatory dependency on `openai-agents`.

The core request/decision/evaluation contracts are testable without the SDK. `make_openai_tool_input_guardrail()` imports the external SDK lazily and returns a native `ToolInputGuardrail` only when the SDK is installed.

This keeps provider/runtime churn outside canonical VALO authority semantics.

## Usage

```python
from agents import Agent, function_tool
from valo_kernel.integrations.openai_agents import (
    ConsequenceDecision,
    GateDisposition,
    make_openai_tool_input_guardrail,
)

async def authorize(call):
    # Production composition: resolve current state, run fresh REHT and RACS,
    # then return a decision bound to call.request_digest.
    return ConsequenceDecision(
        disposition=GateDisposition.ALLOW,
        decision_ref="reht:racs:...",
        evaluated_at=...,
        valid_until=...,
        request_digest=call.request_digest,
        action_digest="...",
    )

gate = make_openai_tool_input_guardrail(authorize)

@function_tool
def transfer(amount: int, currency: str) -> str:
    ...

transfer.tool_input_guardrails = [gate]
agent = Agent(name="governed", tools=[transfer])
```

## Scope

This v1 covers custom OpenAI `FunctionTool` calls because that is where the Agents SDK currently exposes tool input guardrails. Hosted tools and other provider-managed execution surfaces require their own governed effect boundary; they are not silently claimed to be covered by this adapter.
