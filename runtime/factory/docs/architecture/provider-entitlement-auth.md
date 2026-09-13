# Provider-neutral entitlement and authentication

Status: implemented foundation  
Owner: execution worker  
PR: `nsolland/valo-factory#59`  
Canonical base: `d7a802cf209b7d60ed8df4fc80be3cfe5221fef4`

## Decision

Factory provider selection must not assume API-key billing.

The canonical path is:

```text
orchestrator
-> provider entitlement/auth layer
-> provider-specific supported login adapter
-> identity + entitlement + capabilities + quota
-> execution session
-> worker/provider runtime
```

Where a provider officially supports using an existing end-user or enterprise
subscription, that account entitlement is preferred. API credentials remain a
supported fallback, not the default architecture.

## First-class providers

The foundation registers these provider contracts:

- `openai_codex` -> OpenAI Codex / ChatGPT
- `anthropic_claude_code` -> Anthropic Claude Code / Claude
- `google_antigravity` -> Google Antigravity / Google account
- `github_copilot` -> GitHub Copilot / GitHub

`lib/provider_entitlements.py` owns the normalized provider catalog and
deterministic auth-source preference. Provider-specific adapters remain
responsible for discovering whether an official account session, device-code
flow, enterprise identity, or API credential is actually available.

The source identifiers in the catalog are internal contract labels. They are
not OAuth implementations and must not be interpreted as permission to
reimplement, scrape, borrow or bypass a provider login flow.

## Canonical contract

The orchestrator consumes one normalized record:

```text
provider_id
-> adapter_id
-> auth_source
-> auth_mode
-> entitlement_kind
-> entitlement_state
-> identity_ref
-> entitlement_ref
-> capabilities[]
-> quota{}
-> session_ref
-> fallback_used
```

The serialized form is defined by
`schemas/provider-entitlement.schema.json`.

Raw access tokens, refresh tokens, API keys, browser cookies and other secrets
are outside this contract. Provider adapters keep them inside the provider
client or approved secret store and expose only opaque non-secret references.

## Selection rule

Selection is deterministic and provider-specific:

1. use an officially supported account/subscription source when available;
2. otherwise use an officially supported enterprise identity source;
3. otherwise use an officially supported metered API source where the provider
   contract allows it;
4. if none are available, fail closed.

Account entitlement may be reported as `active`, `unknown` or `unavailable`.
An explicitly unavailable entitlement is skipped. An unknown state may be
selected so the provider runtime can perform its own authoritative entitlement
check.

## Provider boundaries

OpenAI: the adapter may consume supported Codex/ChatGPT account or device-code
authentication and fall back to supported enterprise/API authentication.

Anthropic: the adapter may consume supported Claude account authentication and
fall back to supported enterprise/API authentication.

Google: the adapter may consume the supported Antigravity/Google account flow
and fall back to supported enterprise/API authentication. It must not reuse a
Gemini CLI OAuth session or another Google product's login state unless Google
explicitly documents that reuse as supported for the target product.

GitHub: the adapter may consume supported GitHub/Copilot account authentication
and fall back to supported enterprise identity where applicable.

The exact provider command, OAuth endpoint, token format and entitlement probe
belong in provider adapters and must follow current provider documentation.
They are intentionally not hard-coded into the provider-neutral core.

## Authority boundary

Authentication answers who the provider believes the user is.

Entitlement answers which provider capability the account may consume.

Neither answers whether a VALO consequence-bearing action is authorized.

```text
provider auth/entitlement
-> execution capability exists

REHT
-> exact runtime action may happen now
```

Every provider entitlement record therefore carries:

```text
authority_effect = "none"
```

Provider login, subscription state, quota or a successful coding-agent session
must never be treated as a REHT permit, governance clearance or self-attestation.

## Tests

`tests/test_provider_entitlements.py` proves that:

- all four first-class providers are registered;
- subscription/account auth wins over fallback credentials;
- supported fallback is selected when account auth is unavailable;
- explicitly unavailable entitlements are skipped;
- unsupported available auth sources fail closed;
- Google OAuth piggyback/reuse sources are rejected;
- duplicate observations fail closed;
- normalized records contain no credential fields;
- provider state has `authority_effect = none`.

This layer complements the existing provider-neutral model transport contract.
Model transport normalizes inference calls; this layer normalizes identity,
entitlement and execution-session selection for coding-agent providers.
