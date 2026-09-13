# Provider Entitlement/Auth claim

Status: IMPLEMENTED — awaiting CI/QC
Owner: execution worker
Repository: `nsolland/valo-factory`
Canonical base SHA: `d7a802cf209b7d60ed8df4fc80be3cfe5221fef4`
Branch: `feat/provider-entitlement-auth`
Draft PR: `#59`

## Active delivery

Add a provider-neutral entitlement/authentication layer for first-class coding-agent providers so the Factory can use a user's existing subscription or enterprise entitlement where the provider officially supports it, with API/enterprise credentials only as supported fallback.

First-class providers:

- OpenAI Codex / ChatGPT
- Anthropic Claude Code / Claude
- Google Antigravity / Google account
- GitHub Copilot / GitHub

## Owned files

- `work/PROVIDER_ENTITLEMENT_AUTH_CLAIM.md`
- `lib/provider_entitlements.py`
- `schemas/provider-entitlement.schema.json`
- `tests/test_provider_entitlements.py`
- `docs/architecture/provider-entitlement-auth.md`

## Dependencies

- existing provider-neutral model contract
- worker/model provider receipts
- Factory orchestrator provider selection
- provider-supported OAuth/device-code/login contracts

## Boundary

This layer resolves identity, entitlement, auth mode, capabilities, quota metadata and execution-session launch information. It never grants VALO runtime authority and must not bypass, emulate or piggyback unsupported provider authentication flows.

## Evidence

Local isolated contract test: `10/10` passed before commit.
