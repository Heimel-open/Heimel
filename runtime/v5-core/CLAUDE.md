# Claude adapter — VALO V5 Core

Read `AGENTS.md` first. It is the repository working contract.

Then read:

1. `repo-manifest.yaml`
2. `context.md`
3. `README.md`
4. `docs/ARCHITECTURE.md`
5. relevant source, formal specification and focused tests

This file is a Claude-specific adapter. It does not define architecture, authority, current repository state or merge permission.

VALO V5 Core owns deterministic enforcement and protected state-transition mechanisms. It does not create authority or decide whether a proposed action should occur.

Canonical chain:

```text
VAIG evaluation
→ REHT clearance or rejection
→ RACS deterministic decision contract
→ Core or gateway enforcement
→ execution
→ Veritas receipt and observed outcome
```

Protected-change rule:

- Changes to `l1-guardian/` require the matching formal specification and test-vector changes in the same delivery.
- Changes to `formal-verification/` require matching implementation and conformance evidence.
- Do not claim implementation-level proof from specification model checking alone.

Use the commands and current component facts from repository source and documentation, not from this adapter. Remote Git state, exact-commit tests and CI evidence control delivery claims.
