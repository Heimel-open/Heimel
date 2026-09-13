# Work anchor — full semantic architecture map

Repository: `nsolland/valo-reht`
Canonical base SHA: `5ecf09f2ef94c83a04b10a7ef4bcf3becc92a32d`
Branch: `audit/full-semantic-architecture-map`
Owner: Njål / architecture audit

Primary objective: reconstruct and map the complete execution-governance architecture from actual code before any further simplification. Every relevant function/contract must be assigned its original purpose, protected invariant, authority status, runtime position, current destination, and preservation status.

Owned audit files:
- `docs/work-anchors/2026-08-23-full-semantic-architecture-map.md`
- `docs/architecture/full-semantic-function-map.md`
- `docs/architecture/semantic-preservation-ledger.md`
- `docs/architecture/source-coverage-index.md`
- `docs/architecture/symbol-map-execution-substrate.md`

Audit scope starts with the actual execution-governance chain and expands only on concrete code dependencies:
- `valo-kernel`
- `valo-reht`
- `valo-workflow-isa`
- `valo-function-fabric`
- `Racs`
- `valo-gateway`
- `Veritas`
- `VAIG`
- `Baro`
- `valo-platform` containment/egress and execution substrate paths
- `action-attestation-service`

No component is declared redundant merely because it is non-authoritative. No deletion or further architecture reduction is permitted from this audit branch. Missing semantics are blockers for the consolidation claim, not reasons to invent new layers.

Coverage rule: source is classified at symbol/function level. A file is not marked covered until its executable symbols and contracts have been read and assigned a semantic role or explicitly classified as transport/test/reference-only. The audit may add coverage artifacts, but it must not alter production code.
