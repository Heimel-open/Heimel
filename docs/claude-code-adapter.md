# Claude Code governed project adapter

Status: adopted project adapter
Date: 2026-08-11
Owner: VALO Factory

## Decision

VALO adopts Claude Code's repository-local project structure as worker ergonomics, not as an authority model.

Mapping:

- `CLAUDE.md` — project context and canonical worker instructions;
- `.claude/rules/` — modular worker rules;
- `.claude/commands/` — repeatable review/workflow entry points;
- `.claude/skills/` — on-demand capabilities;
- `.claude/agents/` — specialized bounded worker roles;
- `.claude/hooks/` — mechanical preflight adapters;
- `.claude/settings.json` — project-scoped Claude Code configuration.

Canonical invariant:

`capability available != capability authorized`

For consequence-bearing execution the VALO chain remains:

`worker/orchestrator -> VAIG -> reht -> RACS -> external enforcement -> Veritas/receipts`

## PreToolUse adapter

The project registers a PreToolUse command hook for local write/execute tools and all MCP tools. The hook relays the exact Claude Code event to an external executable configured by the deployment in `VALO_REHT_PRETOOL_GATE`.

The external gate must return a Claude Code `PreToolUse` `hookSpecificOutput` containing a final `permissionDecision` of `allow` or `deny`.

The project hook:

- never returns `allow` from local policy or model reasoning;
- fails closed if the external gate is missing, non-executable, unavailable, times out, fails or returns malformed/non-final output;
- accepts only final `allow`/`deny`; Claude-native `ask`/`defer` does not substitute for VALO step-up;
- strips `updatedInput`, so an authorized effect cannot be rewritten after the decision;
- does not create an authority envelope or infer authority from `WORK_CONTRACT.json`.

This is defense in depth, not the trusted PEP. Repository-local Claude hooks can shape/block worker behavior, but trusted execution enforcement remains external to the harness.

## Skills and agents

Skills state how to perform bounded work. Agents define specialized worker roles. They inherit no execution authority from being discoverable or invokable.

The bundled `code-reviewer` agent is read-only (`Read`, `Glob`, `Grep`) and does not self-attest writer output. Independent Factory QC remains the promotion gate.

## MCP

MCP tool availability is capability/context only. Because arbitrary MCP servers may expose external effects, the project PreToolUse adapter sends all `mcp__.*` calls to the external VALO gate rather than guessing which tool names are safe.

## Upstream references

- Claude Code hooks: https://code.claude.com/docs/en/hooks
- Claude Code subagents: https://code.claude.com/docs/en/sub-agents
- Claude Code skills: https://code.claude.com/docs/en/skills

## Non-goals

This adapter does not replace the existing Claude provider adapter, `valo-run`, work contracts, VAIG, reht, RACS, external enforcement, Veritas or independent QC. It adds a governed repository-local Claude Code control surface around the existing Factory architecture.
