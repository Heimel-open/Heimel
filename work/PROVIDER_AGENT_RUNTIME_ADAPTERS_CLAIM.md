# Provider Agent Runtime Adapters claim

Status: IMPLEMENTED — awaiting CI/QC
Owner: execution worker
Repository: `nsolland/valo-factory`
Canonical base SHA: `b2c650ec5fecda31736365595217f8f45275e6f9`
Branch: `feat/provider-agent-runtime-adapters`
Draft PR: `#60`

## Active delivery

Implement provider-specific runtime adapters that launch only vendor-supported authentication and coding-agent session flows behind the provider-neutral entitlement contract.

First-class adapters:

- OpenAI Codex CLI
- Anthropic Claude Code
- Google Antigravity CLI
- GitHub Copilot CLI

## Owned files

- `work/PROVIDER_AGENT_RUNTIME_ADAPTERS_CLAIM.md`
- `lib/provider_agent_adapters.py`
- `bin/valo-agent-provider`
- `schemas/provider-agent-session.schema.json`
- `tests/test_provider_agent_adapters.py`
- `docs/architecture/provider-agent-runtime-adapters.md`

## Dependencies

- `lib/provider_entitlements.py`
- `schemas/provider-entitlement.schema.json`
- vendor-supported CLI auth/session contracts

## Boundary

Adapters may detect installed CLIs, report sanitized auth state, launch documented login commands and construct/run documented non-interactive agent sessions. They must not read raw credential stores, copy OAuth tokens, emulate browser flows or treat provider authentication as VALO authority.

## Evidence

- provider adapter contract tests: `12/12` passed
- Python compile check: passed
- session schema JSON parse: passed
- no dangerous provider permission flags are introduced by the adapter
