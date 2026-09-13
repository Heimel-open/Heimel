# Governed Programmatic Tool Calling (PTC)

Status: adopted architecture pattern for Function Fabric.

## Decision

Programmatic tool calling is supported only as a composition surface over registered, version-pinned Function Fabric functions. Generated Python or other orchestration code never receives execution authority.

Canonical path:

```text
Agent/program -> governed Function stub -> Workflow ISA runtime -> Action Contract
-> REHT -> RACS -> Gateway -> Real World -> Veritas
```

PTC may use branching, loops, fan-out and concurrency to compose calls. Every effectful call remains an independently governed state transition at the execution boundary.

## Invariants

- No direct Python/API execution path.
- Only registered Function identities may be invoked.
- Function versions are pinned before execution.
- Generated orchestration code cannot create, widen or delegate authority.
- Effectful calls must traverse Workflow ISA -> REHT -> RACS -> Gateway.
- A prior permit is not reusable as authority for a later state transition; execution must re-check the current governed state.
- Returned values are treated as runtime results, not as permission to infer or fabricate later observed state.
- Pure/local computation may remain local only when it has no declared external effect.
- PTC composition cannot weaken child risk, authority, evidence, rights, purpose or jurisdiction requirements.
- Veritas receipts remain the record of what actually executed.

## Scope

This pattern belongs inside Function Fabric as an adapter/exposure mode. It is not a new VALO layer and does not alter the canonical authority chain.

## Source signal

Adopted after reviewing arXiv:2608.06370, which shows programmatic tool calling improving tool-use composition and scaling to high fan-out. VALO adopts the composition mechanism while retaining deterministic execution governance at each effectful boundary.
