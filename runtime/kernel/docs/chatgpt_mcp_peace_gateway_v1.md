# ChatGPT custom MCP -> PEACE gateway v1

## Purpose

ChatGPT custom MCP apps are treated as a capability and transport layer. They may expose read, write and modify tools, and ChatGPT/workspace controls may decide whether a tool is visible, enabled or requires user confirmation. None of those facts mint PEACE authority.

The governed path is:

```text
ChatGPT proposes custom MCP action
  -> exact app/server/tool/arguments/context normalized
  -> PEACE/VALO consequence-time authorization
       -> fresh authority / revocation state
       -> exact effect binding
       -> ALLOW / DENY / ESCALATE
  -> ALLOW + fresh exact binding -> remote MCP invocation
  -> provider result digest + deterministic receipt
  -> anything else -> zero provider effect
```

## ChatGPT context binding

The adapter binds the following ChatGPT-side context into the canonical effect digest when supplied:

- app identifier
- workspace identifier
- frozen tool snapshot reference
- whether the workspace currently marks the action enabled
- whether ChatGPT/user confirmation occurred
- conversation reference

These fields are evidence/context only. `action_enabled=True` or `user_confirmed=True` does not produce an ALLOW decision.

## Exact effect

The governed request binds:

- MCP server id
- tool name
- original tool arguments
- principal and actor
- purpose and mandate reference
- request timestamp
- ChatGPT context

Changing any bound field changes the effect digest. An authorization for a different digest fails closed.

## Consequence-time rule

The remote MCP provider is unreachable until fresh authorization for the exact normalized request returns ALLOW and remains current at the commit/effect boundary. Missing, stale, denied, escalated or mismatched authorization produces a receipt with `invoked=false` and no MCP call.

## Relationship to ChatGPT controls

ChatGPT-side controls remain useful defense in depth:

- workspace app approval controls availability
- per-action controls constrain which tools ChatGPT can attempt
- frozen tool snapshots constrain approved definitions
- confirmation can provide explicit user-intent evidence

PEACE sits below that layer and independently decides whether the concrete effect is authorized now.

Therefore:

```text
capability available != authority to use it
workspace approval != consequence-time authority
user confirmation != consequence-time authority
```

## Existing kernel reuse

This adapter deliberately reuses the existing generic MCP bridge and canonical consequence-time gate. It adds only ChatGPT-specific normalization/context binding and does not create a second authorization path.

## Scope

v1 covers consequence-bearing calls from ChatGPT custom MCP apps to a remote MCP server. It does not claim that ChatGPT itself supplies fresh PEACE authority. It does not treat provider success as authoritative truth; provider output is digest-bound into the invocation receipt as evidence.
