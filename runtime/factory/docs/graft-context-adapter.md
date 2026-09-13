# Graft governed code-context adapter

Status: implemented
Date: 2026-08-13
Owner: nsolland
Upstream: `NanoNets/Graft`
Validated upstream commit: `d834ca227d765b2736cfeafb97b0e71e2ea21d50`
Validated package version: `0.11.0`
Contract: `valo.graft-context-policy.v1`

## Decision

VALO Factory adopts Graft as a replaceable code-understanding/context engine for software workspaces.

Graft may provide:

- deterministic tree-sitter code graph and symbol/call relationships;
- repository maps, grep, callers and skeleton views;
- freshness checks against the current working tree;
- multi-repository context federation;
- optional LLM-generated context when explicitly enabled against a private endpoint.

Graft does not become part of Kernel, Lens, reht or the authority model.

Canonical boundary:

`code/repositories -> Graft context evidence -> governed workspace -> worker -> proposed diff -> independent conformance/QC -> fresh authority -> VAIG -> reht -> RACS -> external PEP -> merge/execution -> receipt`

`context available != state admitted != action authorized`

## Wrapper

Factory exposes Graft through `bin/valo-graft`, not through `graft init`.

Allowed commands are narrowed by `config/graft_policy.json` and by a hard-coded maximum set in the wrapper:

- `build`
- `check`
- `grep`
- `map`
- `callers`
- `skeleton`
- `ask` only under the private-LLM gate

The wrapper never exposes `init`, `upgrade`, `mcp`, `viz`, `version` or `_update-check`.

This prevents an agent from using the Factory integration to install machine-global Codex/MCP configuration, mutate the global Graft installation, start an ungoverned server surface, or deliberately trigger the registry update path.

## Structural mode

Structural Graft operation is the default.

Before execution the wrapper:

1. requires `graft/` to already be ignored in every target git root, so upstream has no reason to modify `.gitignore`;
2. removes ambient OpenAI, Anthropic and OpenRouter credentials from the child process;
3. removes Graft provider/model/key/base-URL settings;
4. places Graft in an isolated temporary HOME;
5. seeds Graft's update cache with a fresh local record so its CLI pre-action has no reason to spawn the detached npm registry check.

The resulting structural code graph is context evidence only. It grants no rights and cannot approve a proposed change.

## LLM-backed mode

`graft ask` and `graft build --deep` are disabled unless all of the following hold:

- deployment sets `VALO_GRAFT_ALLOW_LLM=1`;
- `GRAFT_API_KEY` is present;
- `GRAFT_BASE_URL` is `localhost` or a literal private/link-local IP address;
- provider is OpenAI-compatible (`GRAFT_PROVIDER=openai`, or omitted and forced to `openai`).

Public hostnames and native public model-provider routes fail closed. CLI `--api-key` and `--base-url` are rejected to keep secrets/endpoints out of command arguments and logs.

This is a data-boundary control, not an authority mechanism. A deployment that permits LLM summaries remains responsible for the private model endpoint and data-handling policy.

## Upstream maintenance

The validated upstream snapshot is Graft `0.11.0` at commit `d834ca227d765b2736cfeafb97b0e71e2ea21d50`.

Production installation should pin that package version until a new upstream version has passed Factory compatibility/conformance checks:

```bash
npm install -g @nanonets/graft@0.11.0
```

Upstream is external and replaceable. Updating or replacing it must not alter the governed workspace contract or the execution-authority chain.

## Multi-repo use

Graft can federate context across a workspace containing multiple git children. `valo-graft` checks every immediate git child before a workspace build and requires each child to pre-ignore `graft/`.

The graph can therefore help a worker understand cross-repository dependencies without collapsing repository ownership, claims, branch scope or merge authority.

## Non-goals

This adapter does not:

- admit information into operative enterprise state;
- determine semantic standing or provenance;
- grant worker capabilities or authority;
- approve a diff;
- replace independent QC/conformance;
- merge or push code;
- execute production effects;
- replace VAIG, reht, RACS, PEP or receipts.

Graft answers what the code is and how it is connected. VALO decides what work is in scope and whether any proposed consequence may occur.
