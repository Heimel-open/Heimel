# Governed Workspace v1 work anchor

- Repository: `nsolland/valo-kernel`
- Canonical base: `b947ac8d783ec54e80ec14749cecdccfb54921eb`
- Branch: `agent/governed-workspace-v1`
- Owner: Codex on behalf of Njål / VALO
- Active delivery: deterministic governed projection, bounded workspace and candidate conformance over authoritative WorldState
- Owned files: workspace contracts/compiler/conformance, execution-context binding, focused tests, exports and architecture documentation
- Dependencies: existing Kernel WorldState, state-root integrity, purpose, provenance and truth-status contracts
- Non-goals: worker execution, authorization, external side effects, model evaluation or a second state owner

Founder decision: govern the space, not the worker. Workers receive a bounded projection and return non-authoritative candidates. REHT remains the sole authorization boundary.
