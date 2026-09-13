# valo-skills-registry

Canonical **skill** registry for VALO. A skill is an installable, versioned
execution module. This repo is the deterministic **catalog and contract layer** —
it does NOT evaluate, authorize, or execute.

## Responsibility split (hard boundary)

| Repo | Owns |
|------|------|
| `valo-skills-registry` | canonical skill manifests: versions, dependencies, risk class, I/O contracts, provider metadata |
| `valo-runtime-core` | loads, resolves and binds skills at runtime |
| `valo-tool-adapters` | implementations against concrete tools/APIs |
| `valo-runtime-adapters` | bindings to OpenAI, Gemini, Claude, local runtimes, other agent frameworks |
| `valo-mcp` | exposes approved skills over MCP |
| `valo-distribution` | packages and distributes approved skill packages |
| `valo-platform` | governance, authorization, existing capability registry |

## Skill != Capability != Mandate != Adapter
- **Skill**: installable, versioned execution module.
- **Capability**: what the agent can in principle do.
- **Mandate**: what the agent is allowed to do now.
- **Adapter**: how the action is wired to a concrete system.
- **REHT**: whether the concrete execution is cleared.
- **RACS**: expresses the deterministic decision.
- **Gateway**: enforces the decision.

## Architecture rule
The Skills Registry must NOT evaluate, authorize or execute. It is a deterministic
catalog/contract layer. The existing `capability_registry` in `valo-platform` is
kept as the governance link between a skill and its allowed capability — so we avoid
mixing module distribution with authority.

## Proposed flow
```
Agent
  → Skills Registry            (lookup manifest by id+version)
  → Skill Resolver             (runtime-core: resolve deps, bind)
  → Capability Mapping         (valo-platform capability_registry)
  → VAIG evidence
  → REHT clearance
  → RACS contract
  → Tool/runtime adapter
  → Execution gateway
  → Veritas receipt
```

## Minimum manifest
See `schemas/skill.schema.json` and `skills/` for reference skills.
