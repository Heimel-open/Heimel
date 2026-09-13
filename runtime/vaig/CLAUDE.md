# Claude adapter — VAIG

Read `AGENTS.md` first. It is the repository working contract.

Then read:

1. `repo-manifest.yaml`
2. `SYSTEM_MAP.md`
3. `README.md`
4. `canonical.md`
5. relevant source, schemas and focused tests

This file is a Claude-specific adapter. It does not define architecture, authority, current repository state or merge permission.

VAIG is the smart evaluation layer. It observes evidence, risk, uncertainty, policy signals and trajectories, then produces evidence-backed recommendations.

VAIG does not:

- grant authority or execution clearance
- perform the downstream side effect
- turn a model score into permission
- replace REHT
- redefine the RACS contract

Canonical chain:

```text
proposal and evidence
→ VAIG evaluation and recommendation
→ REHT clearance or rejection
→ RACS deterministic decision contract
→ gateway or execution-boundary enforcement
→ execution
→ Veritas receipt and observed outcome
```

Outcome labels produced by VAIG are recommendations or evaluation states unless an exact repository contract states otherwise. They are never self-authorizing.

Repository source, current schemas, tests, remote Git state and CI evidence remain authoritative.
