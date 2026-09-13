# Provider coding-agent runtime adapters

Status: implemented
Owner: execution worker
PR: `nsolland/valo-factory#60`
Canonical base: `b2c650ec5fecda31736365595217f8f45275e6f9`

## Decision

The Factory now has one runtime launcher for the four first-class coding-agent
providers. The provider-neutral layer does not implement OAuth. It invokes only
the provider's own documented CLI authentication and session surfaces.

```text
Factory orchestrator
-> provider entitlement/auth contract
-> valo-agent-provider
-> vendor CLI
-> vendor-supported login/session
-> provider output + sanitized execution receipt
```

The supported providers are:

- OpenAI Codex CLI
- Anthropic Claude Code
- Google Antigravity CLI
- GitHub Copilot CLI

## CLI

`bin/valo-agent-provider` exposes:

```text
providers
status <provider>
login <provider> [--headless] [--dry-run]
plan <provider> [--prompt/--prompt-file/stdin]
run <provider> [--prompt/--prompt-file/stdin]
```

`status` never reads provider credential files, keychains, browser cookies or
OAuth refresh tokens. It uses only installed-binary checks, documented safe
status/probe commands, and the presence (not value) of documented credential
environment variables.

`plan` returns only a prompt digest and fixed command surface. The raw prompt is
not written into the receipt.

`run` invokes the provider binary without a shell and emits a
`VALO_PROVIDER_RECEIPT` on stderr. The receipt stores digests of prompt/stdout/
stderr rather than their contents.

## Provider contracts

### OpenAI Codex

Login:

```text
codex login
codex login --device-auth
codex login status
```

Execution:

```text
codex exec --json --ephemeral --sandbox <read-only|workspace-write> -
```

The prompt is sent on stdin, not exposed in the process argument list. Codex
documents that `codex exec` reuses saved CLI authentication; ChatGPT-managed
account auth can therefore remain the selected subscription path.

References:
- https://learn.chatgpt.com/docs/non-interactive-mode
- https://github.com/openai/codex

### Anthropic Claude Code

Login:

```text
claude login
```

Execution uses the documented non-interactive `claude -p` surface with
stream-JSON output. `ANTHROPIC_API_KEY`, when present, is reported only as an
auth-mode conflict/fallback signal because Anthropic documents that it takes
precedence over subscription authentication.

The adapter intentionally does not spend a Claude model call merely to discover
subscription login state. Without an API key, auth is reported as `unknown`
until the provider session verifies it.

References:
- https://support.claude.com/en/articles/11145838-use-claude-code-with-your-pro-or-max-plan
- https://support.claude.com/en/articles/14554922-claude-code-user-faq

### Google Antigravity

Login is delegated to `agy`. Google's current CLI presents supported login
choices including Google OAuth and Google Cloud project authentication.

Auth probing uses:

```text
agy models
```

A successful probe proves Antigravity can access its provider runtime, but the
neutral adapter does not infer whether that session came from personal Google
OAuth or Google Cloud. No OAuth files are inspected, and
`--dangerously-skip-permissions` is never added by the adapter.

Execution:

```text
agy -p <prompt>
```

Reference:
- https://codelabs.developers.google.com/antigravity-cli-hands-on

### GitHub Copilot

Login:

```text
copilot login
```

GitHub documents this as an OAuth device flow. Copilot may also use supported
environment-token or GitHub CLI authentication. The adapter checks only whether
the documented token variables are present and may use `gh auth status` as a
sanitized GitHub-account signal. Copilot itself remains responsible for
verifying Copilot license and organization policy when a session starts.

Non-interactive execution uses the documented prompt mode and explicit tool
permissions.

References:
- https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference
- https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference

## Execution profiles

`read_only` is the review/judgment profile.

`workspace_write` is the isolated writer/worker profile.

The adapter never enables unrestricted/dangerous provider modes itself. Any
broader permission profile requires a separate explicit Factory change and must
remain bounded by the existing worktree/claim/QC architecture.

## Authority invariant

Provider authentication answers whether the provider runtime can be used.
Provider execution answers what the coding agent did.

Neither grants VALO authority.

Every status, plan and execution receipt carries:

```text
authority_effect = "none"
```

REHT remains the only runtime authorization boundary for consequence-bearing
VALO actions.
