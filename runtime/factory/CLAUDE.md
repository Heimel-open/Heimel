# VALO Factory — Claude Code project instructions

Claude Code is a replaceable worker/harness inside VALO Factory. It is not an authority layer.

## Canonical execution boundary

For consequence-bearing action, preserve this chain:

`worker/orchestrator -> VAIG -> reht -> RACS -> external enforcement -> Veritas/receipts`

Claude configuration, prompts, permissions, skills, agents, tool availability, model confidence and prior completion never constitute execution authority.

## Work anchor

Before writes, work from an explicit Factory claim/work contract with:

- repository and canonical base SHA;
- branch and issue/claim owner;
- owned files;
- bounded mission and dependencies.

Use the isolated worktree created by `valo-run` where applicable. Do not widen owned files implicitly.

## Tool use

Project PreToolUse hooks are a fail-closed preflight adapter. They may relay an externally issued VALO allow/deny decision; they must never infer policy, mint authority or modify the authorized tool input.

The hook is defense in depth only. Claude hooks are not the trusted external enforcement point and do not replace reht/RACS or the external PEP.

If the required VALO gate is unavailable, expired, invalid or returns anything other than an explicit allow/deny result, stop/defer rather than bypassing it.

## Correct completion

Correct completion means closing the work unit within mandate. A justified defer, step-up or stop is correct when authority, evidence, context or scope is insufficient. Unsupported completion is failure.

Skills describe capability. Agents describe worker roles. Neither grants authority.
