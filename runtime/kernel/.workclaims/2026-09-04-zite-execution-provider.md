# Work claim — Zite execution provider

Owner: ChatGPT / Njål
Date: 2026-09-04
Base SHA: 6459f1ef0f1fe248d5425d22d8ca679448e3d61c
Branch: adopt/zite-execution-provider

## Active delivery
Adopt Zite as an optional external execution provider pattern without making it a Kernel dependency.

## Owned files
- `.workclaims/2026-09-04-zite-execution-provider.md`
- `docs/zite_execution_provider_v1.md`

## Dependency boundary
Zite remains replaceable and external. Kernel, REHT, Gateway, Veritas and native test paths must remain operable with zero Zite dependency.

## Goal
Define how a consequence-bearing Zite/MCP/workflow action is admitted only after fresh VALO authorization, how the exact action is bound to the execution grant, and how Zite run/webhook evidence is correlated into Veritas without treating provider logs as authoritative truth.
