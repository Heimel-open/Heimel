# Serena governed semantic code adapter

Status: implemented
Date: 2026-08-15
Owner: nsolland
Upstream: `oraios/serena`
Validated release: `v1.7.0`
Validated upstream commit: `949a27ef1e5fda1a6e7b561e777bcece345c6ffd`
Contract: `valo.serena-semantic-adapter.v1`

## Decision

VALO Factory adopts Serena as an optional, replaceable semantic code-intelligence MCP adapter for coding workers.

Serena may provide symbol-aware retrieval, reference lookup, diagnostics, symbolic editing, rename, safe delete and backend-specific refactoring. It is not an authority source, orchestrator, governed state store, execution policy engine or receipt system.

Canonical boundary:

`governed workspace -> Serena semantic MCP -> coding worker -> proposed diff -> tests -> independent QC/conformance -> fresh authority -> VAIG -> reht -> RACS -> external PEP -> GitHub/external effect -> receipt`

`semantic capability != authority`

## Containment

Factory exposes Serena through `bin/valo-serena`.

The launcher requires:

- `VALO_WORKSPACE_ROOT` to identify the governed workspace boundary;
- the selected project to resolve inside that workspace;
- `VALO_SANDBOX_ATTESTED=1` from the execution substrate;
- Serena to run over stdio only;
- the `ide` context;
- the `no-memories` mode;
- the web dashboard disabled;
- ambient production credentials removed before the child process starts.

CubeSandbox is the preferred execution substrate. An equivalent isolated substrate is acceptable if it provides the same workspace, credential and process-containment guarantees.

Serena is therefore allowed to be consequence-capable inside the disposable/bounded software workspace, but it receives no direct production effect path.

## Memory and state

Serena memory is disabled in the Factory launcher.

If a deployment later enables any Serena cache, index or memory outside this launcher, that material remains non-authoritative context only. It cannot become Kernel state, revive stale authority, widen scope, approve a diff or substitute for current code/tests/evidence.

Canonical Factory state remains provider-neutral.

## Credentials

The launcher strips common ambient provider and cloud credentials before Serena starts, including GitHub, AWS, Azure, Google, OpenAI and Anthropic credentials.

This is defense in depth, not the authority mechanism. Execution authority remains outside Serena and is only consumed at the governed effect boundary.

Workers that need to inspect private dependencies must receive narrowly scoped workspace-local material through the sandbox rather than host-level production credentials.

## MCP surface

The governed launcher fixes the MCP transport to stdio. It does not expose Serena's HTTP/SSE server modes or dashboard.

The default `ide` context is used because Factory workers already own generic file/shell orchestration; Serena is adopted specifically for semantic IDE capabilities rather than as a second general-purpose shell surface.

The `no-memories` mode removes Serena memory/onboarding tools from this governed integration.

## Upstream pin

The validated upstream snapshot is Serena `v1.7.0` at commit `949a27ef1e5fda1a6e7b561e777bcece345c6ffd`.

Install a validated package version in the sandbox image rather than allowing workers to install or upgrade Serena themselves. Upstream replacement or upgrade requires adapter compatibility/conformance tests but must not change VALO governance semantics.

Reference installation shape:

```bash
uv tool install -p 3.13 serena-agent==1.7.0
```

## Launch

The execution substrate sets the workspace and sandbox attestation, then launches:

```bash
VALO_WORKSPACE_ROOT=/workspace \
VALO_SANDBOX_ATTESTED=1 \
python3 bin/valo-serena --project /workspace/repo
```

The launcher constructs the Serena command itself. Workers do not supply arbitrary Serena server flags.

## Invariants

1. Serena is replaceable without changing governance contracts.
2. Serena semantic results and diagnostics are context/evidence, not authority.
3. Serena memory is disabled and non-authoritative.
4. Serena runs inside a bounded sandbox workspace.
5. Serena receives no ambient production credentials.
6. Serena does not expose a remote MCP listener through the Factory adapter.
7. No consequence-bearing external effect may bypass independent QC, fresh authority, reht/RACS and the governed PEP path.
8. DENY/DEFER/STEP_UP/HALT remain null-effect outcomes at the external effect boundary.

## Non-goals

This adapter does not replace Graft. Graft remains useful as a deterministic structural repository/context engine; Serena adds live symbol-aware IDE semantics and refactoring for coding workers.

It also does not replace Kernel, Lens, VAIG, reht, RACS, the external PEP/Gateway, Veritas, tests or independent QC.
