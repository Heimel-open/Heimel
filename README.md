# valo-runtime-core

Canonical interfaces and contracts for the VALO runtime layer. This is the
**single source of truth for the runtime contract**. No runtime implementation
lives here — only the interfaces, event model, and contracts that every runtime
adapter (local, harness, google, openai, claude) and every tool adapter must
satisfy.

## Purpose

Make the runtime an interchangeable component. VALO's core is evaluation, authorization,
decision contracts and evidence. Agent engines and tools can be swapped or
combined without changing the governing logic (VAIG → REHT → Veritas).

## Canonical architecture

```
Application
      │
      ▼
Runtime Interface
      │
 ┌────┼──────────────────────┐
 │    │          │    │       │
Local Harness  Google OpenAI Claude   (runtime adapters)
 │
 ▼
VAIG (evaluates)
 │
 ▼
REHT (clears exact action & issues Execution Permit carrying RACS contract data)
 │
 ▼
Tool Interface (GitHub, Gmail, Slack, Docker, Kubernetes, MCP, REST)
 │
 ▼
Execution
 │
 ▼
Veritas (proves)
```

## Repos in this architecture

| Repo | Role |
|------|------|
| `valo-runtime-core` | This repo — interfaces + contracts (no impl) |
| `valo-runtime-local` | Reference runtime: local process execution, checkpoint/restart, event stream |
| `valo-runtime-adapters` | HarnessRouter, Google Agent Platform, OpenAI Agents, Claude Code |
| `valo-tool-adapters` | GitHub, Gmail, Google Drive, Slack, Docker, Kubernetes, SSH, MCP, HTTP/REST |

## Hard boundaries

- No tool adapter may perform a consequential action directly. All actions require valid REHT clearance.
- VAIG evaluates evidence and risk. VAIG has no execution authority.
- REHT clears or denies the exact action. REHT is the sole authorization boundary.
- RACS is dumb, immutable decision contract data carried inside the Execution Permit produced by REHT.
- Veritas records authorization, execution attempts, and observed outcomes.
- Swapping a vendor must require NO code change in `valo-runtime-core`.
