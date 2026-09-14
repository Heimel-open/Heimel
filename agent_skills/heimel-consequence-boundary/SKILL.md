---
name: heimel-consequence-boundary
description: Route consequence-bearing agent actions through Heimel instead of allowing direct effects. Use when an agent may write, send, publish, mutate, deploy, pay, delete, approve, revoke, invoke privileged tools, or otherwise cause an external consequence.
license: Apache-2.0
metadata:
  author: Heimel-open
  version: "0.1.0"
---

# Heimel Consequence Boundary

Use this skill when intent may become an external consequence.

The agent may reason, inspect, draft, simulate, and prepare locally. It must not execute a consequence-bearing action directly.

Required path:

intent -> Heimel contract/profile -> fresh authority check at consequence time -> governed effect path -> verifiable evidence/receipt

Rules:

1. Never trust caller-supplied consequence classification. Treat effect classification as owned by the governed runtime/tool registry.
2. Never bypass Heimel because an action looks low-risk, reversible, routine, previously approved, or already discussed.
3. Never reuse stale authority. Authority must be resolved fresh at consequence time.
4. Never execute a consequence-bearing action through an ungoverned shell, SDK, browser action, API call, MCP server, plugin, or direct tool path.
5. Unknown or unregistered effect classification fails closed.
6. If the Heimel governed effect tool/path is unavailable, stop before the effect and report that the consequence boundary is unavailable.
7. A draft, plan, command preview, patch, request body, or dry run is not execution. Keep it non-operative until Heimel authorizes and executes the effect.
8. Do not treat this skill itself as an authorization mechanism. This skill routes to Heimel; Heimel remains the authority/effect boundary.

Before a consequence-bearing action, run the local preflight helper:

python scripts/heimel_preflight.py --profile "$HEIMEL_PROFILE" --runtime-id "$HEIMEL_RUNTIME_ID" --environment live

The helper validates and compiles the governed profile and emits a session descriptor. It does not authorize or execute the effect.

Then invoke the Heimel-governed runtime/tool exposed by the environment. Pass the exact operative intent and bindings required by that tool. Do not substitute a direct effect path.

If the environment exposes no Heimel-governed effect tool, do not execute the effect.

Expected successful completion evidence:

- Heimel decision/result for the exact action
- exact state/effect binding
- consequence-time authority result
- verifiable receipt/evidence reference

For non-consequence work, continue normally.
