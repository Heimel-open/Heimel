# REHT Legacy Reconciliation — 2026-08-18

Status: review candidate
Issue: `nsolland/valo-reht#27`
Canonical runtime base: `nsolland/valo-reht@df0c80de1be53e4380a0fdd6e2da6c7fb94736b8`
Legacy source inspected: `nsolland/reht@8cbcd3b94f333a36ec5605b166049bf430b21a07`
Standards owner inspected: `nsolland/reht-standard`
RACS owner inspected: `nsolland/Racs`

## Decision boundary

`nsolland/valo-reht` remains the sole VALO runtime execution-authorization owner.

`nsolland/reht-standard` remains the public REHT-specific standards/conformance owner.

`nsolland/Racs` remains the deterministic decision/action/permit/receipt contract owner.

Legacy material is not imported because it exists. It is retained only if it supplies a current property not already owned by those canonical surfaces.

## Classification outcomes

- `MIGRATE_RUNTIME`
- `MOVE_STANDARD_PROPOSAL`
- `MOVE_DOMAIN_PROFILE`
- `MOVE_RESEARCH_EVIDENCE`
- `HISTORICAL_ONLY`
- `REJECT_CONFLICTING_OR_STALE`
- `NOT_ESTABLISHED`

## 1. Legacy package identity and manifest

Inspected:

- `repo-manifest.yaml`
- `README.md`
- `pyproject.toml`
- `src/reht/__init__.py`

Legacy claims include `canonical_role: positive_clearance_boundary`, `normative_status: normative_specification`, package `reht-governance` v0.2.0, and executable clearance/issuance ownership.

Classification: `REJECT_CONFLICTING_OR_STALE` as current ownership.

Reason:

The current architecture already assigns runtime authorization to `valo-reht`, public REHT standards/conformance to `reht-standard`, and RACS contracts to `Racs`. Keeping the legacy manifest/package identity active would recreate parallel authority ownership.

Preserve repository history as provenance; do not preserve the ownership claim.

## 2. Draft 0.1 admissibility specification

Inspected: `SPECIFICATION.md`.

Legacy semantics include:

- `ADMISSIBLE`
- `INADMISSIBLE`
- `INDETERMINATE`
- `REQUIRES_STEP_UP`
- `NO_LONGER_ADMISSIBLE`
- statement that VAIG orchestrates runtime evaluation and Core enforces execution-state transitions.

Classification: `REJECT_CONFLICTING_OR_STALE` as runtime specification.

Reason:

The document predates the current minimum consequence architecture and current component ownership. Current runtime `RealReht` is deliberately bounded to fresh exact-action `ALLOW`/`DENY`; wider decision semantics are carried by the RACS contract. Public admissibility semantics, where still useful, belong only through `reht-standard` governance.

No runtime migration.

## 3. Legacy `RehtIssuer` / RACS v0.2 issuance stack

Inspected:

- `src/reht/issuance.py`
- `src/reht/issuance_policy.py`
- `src/reht/payloads.py`
- `src/reht/artifacts.py`
- `src/reht/boundary_issuance.py`
- `src/reht/racs_v02_adapter.py`
- exported `BoundaryChainVerifier`, `RacsV02BoundaryVerifier`, `RehtIssuer` surfaces in `src/reht/__init__.py`
- current RACS v0.2 model/binding ownership in `nsolland/Racs`.

Legacy behavior includes signed `ADMISSIBILITY_DETERMINATION` and `GOVERNANCE_CLEARANCE` issuance, local RACS canonicalization/signing/boundary verification, and clearance production for `ALLOW` and `MODIFY` / `CONDITIONALLY_ADMISSIBLE` paths.

Classification: `REJECT_CONFLICTING_OR_STALE` as canonical runtime implementation.

Reason:

The legacy package combines REHT authorization with RACS-owned wire/artifact responsibilities and admits a `MODIFY` clearance path that is outside the current canonical runtime authorization semantics. RACS now owns deterministic decision/action/permit/receipt contracts and reference bindings. Current `valo-reht` owns only the fresh authorization decision and bound permit references.

No wholesale migration. Any future signed artifact implementation must consume the canonical RACS contract rather than re-own it inside REHT.

## 4. RACS codec, schema, trust and artifact verification utilities

Inspected legacy surfaces:

- `src/reht/racs_codec.py`
- `src/reht/racs_validation.py`
- `src/reht/verification.py`
- `src/reht/trust.py`
- `src/reht/crypto.py`

These implement RACS-JCS canonicalization/digests, RACS schema validation, Ed25519 artifact verification and issuer/key trust resolution around legacy RACS artifacts.

Classification: `REJECT_CONFLICTING_OR_STALE` as REHT-owned infrastructure.

Reason:

These are contract transport/integrity utilities, not the fresh authorization judgment. Current RACS reference bindings and the appropriate trust/integrity owners should supply these properties. Duplicating them inside REHT would make REHT a second RACS implementation and a second trust registry.

No runtime migration unless a later concrete canonical-runtime dependency proves a missing generic verifier; none was established in this pass.

## 5. Governed Workspace authorization

Inspected legacy surfaces:

- `src/reht/workspace_clearance.py`
- workspace binding fields in `src/reht/artifacts.py`, `issuance_policy.py` and `payloads.py`
- `docs/governed-workspace-clearance.md`

Inspected canonical surfaces:

- `src/valo_reht/governed_workspace.py`
- current `RealReht` integration
- commit `a13719ed015d13915f3264ee55236965b8fe9de2` (`Move Governed Workspace authorization into canonical REHT runtime`).

Classification: `HISTORICAL_ONLY` / already migrated.

Reason:

Canonical `valo-reht` already verifies tenant-bound Ed25519 Kernel context origin, exact workspace/action lineage, context freshness, workspace expiry, dependency/state continuity, purpose and target continuity, and explicitly refuses workspace authority creation before `RealReht` evaluates current authority.

The legacy implementation does not establish a missing runtime property.

No runtime migration.

## 6. Normative VAIG handoff / non-execution determination

Inspected: `src/reht/normative_clearance.py` and associated tests.

Legacy behavior accepts VAIG `DEFER` / `STEP_UP` handoffs and issues signed non-execution `ADMISSIBILITY_DETERMINATION` artifacts with `INDETERMINATE` / `REQUIRES_STEP_UP` states while deliberately refusing GovernanceClearance.

Classification: `REJECT_CONFLICTING_OR_STALE` as REHT runtime behavior.

Reason:

The non-execution safety intent is valid, but REHT does not need to own a second outcome plane or issue a parallel determination artifact for VAIG recommendations. VAIG outputs are evidence/evaluation; RACS owns the wider deterministic decision contract; current `valo-reht` answers only whether the exact effect is currently authorized. A restrictive upstream outcome can simply result in no executable effect or an appropriately bound RACS decision without expanding REHT semantics.

No runtime migration.

## 7. Post-boundary external handoff receipt

Inspected: `src/reht/post_boundary.py`.

Legacy behavior signs an `EXECUTION_HANDOFF_RECEIPT` that binds a GovernanceClearance to an external request, target and correlation id. It treats both `ALLOW` and `MODIFY` / conditionally-admissible clearances as handoff-eligible.

Classification: `REJECT_CONFLICTING_OR_STALE` as REHT-owned runtime behavior.

Reason:

Exact effect binding after authorization is a real required property, but current ownership is the RACS binding contract plus Gateway bounded dispatch and Veritas effect/outcome proof. REHT should not issue a second post-authorization handoff artifact or make `MODIFY` executable. If an interoperable handoff envelope is needed, it belongs in RACS/Gateway contract work, not in the authorization kernel.

No runtime migration.

## 8. Cancellation authorization

Inspected:

- `src/reht/cancellation.py`
- `tests/test_cancellation_authorization.py`.

Legacy behavior validates a signed cancellation request and issues a distinct signed `CANCELLATION_AUTHORIZATION` with decision `HALT` bound to task, permit and commit token.

Classification: `REJECT_CONFLICTING_OR_STALE` as a special REHT runtime path; semantic intent retained.

Reason:

Stopping an active consequence can be necessary, but cancellation does not require a second authorization mechanism. Cancellation itself can be represented as an exact consequence-bearing action/capability, evaluated against fresh authority and executed through the same governed effect path. Any portable cancellation/`HALT` binding belongs in the RACS/workflow/Gateway contract surfaces. A dedicated REHT cancellation artifact would reintroduce a parallel path.

No runtime migration.

## 9. Agent Skills binding

Inspected legacy surfaces:

- `skill_context` validation in `src/reht/issuance_policy.py`
- `skill_binding_digest` carried in `src/reht/payloads.py`
- commit `7c84d4aee7ff5eecaa18e232c5bfe95e10d8fe26`.

Classification: `NOT_ESTABLISHED` as a runtime requirement; default disposition is no migration.

Reason:

The binding proves identity/version/source/hash/provenance/requested-capability metadata for a skill, but no evidence inspected establishes that a dedicated REHT-specific `skill_binding_digest` is an irreducible runtime property beyond the canonical exact action, evidence, capability, authority and contract bindings. Skill metadata has a separate canonical owner.

If a portable skill-binding requirement is still desired, propose it through the relevant skill/RACS/REHT-standard contract owner. Do not import the legacy field into runtime merely for compatibility with an unestablished consumer.

## 10. External security verifier attestation

Inspected:

- `src/reht/security_attestation.py`
- `docs/architecture/EXTERNAL_SECURITY_VERIFIERS.md`
- `schemas/security-finding-attestation-v1.schema.json`
- commit `af40023d1f3b91c42bd69c79b2060ba6b72688d0`.

The legacy design correctly treats external security verifiers as evidence producers, not authority sources, and binds findings to an exact repository/commit and evidence digest. The code maps evidence into legacy `ADMISSIBLE`, `INADMISSIBLE`, `INDETERMINATE` and `REQUIRES_STEP_UP` states.

Classification: `MOVE_STANDARD_PROPOSAL` / external-evidence profile candidate; not `MIGRATE_RUNTIME`.

Reason:

The evidence schema and negative-path semantics may remain useful, but the evaluator's legacy admissibility outcome vocabulary must not become a second REHT decision plane. Producer adapters belong in the external-adapter/evidence substrate; transport/signature contracts remain RACS-owned; any normative REHT evidence requirement must enter `reht-standard` through governance.

No runtime migration in this reconciliation PR.

## 11. Sustainability / CSRD-ESRS action profile

Inspected:

- `src/reht/sustainability_action_profile.py`
- `docs/profiles/CSRD_ESRS_ACTION_CLEARANCE_PROFILE_V1.md`
- `tests/test_sustainability_reporting_action_profile.py`
- commit `638f4baee4768a3caf458292d0b9325952982284`.

The profile declares domain action classes and required reporting context while explicitly stating that it does not authorize.

Classification: `MOVE_DOMAIN_PROFILE`.

Reason:

Domain action taxonomies do not belong in the generic authorization kernel. If retained, this material belongs in a sustainability/reporting domain pack/profile that submits exact action contracts to canonical `valo-reht`.

No runtime migration.

## 12. Research, evidence, claims and manuscript material

Inspected repository search/history includes:

- `research/beyond_trusted_monitoring_benchmark.py`
- `.claims/beyond-trusted-monitoring-paper-v1.md`
- `.claims/post-execution-evidence-chain-v1.md`
- `docs/evidence/*`
- `docs/ip/IP_PROVENANCE.md`
- independent execution-authorization manuscript material at current legacy head.

Classification: `MOVE_RESEARCH_EVIDENCE` where still useful; otherwise `HISTORICAL_ONLY`.

Reason:

Research can support architecture and standards without owning runtime semantics. Publication/research material should be retained through the research/publication owner or immutable repository history. Claims documenting already-migrated runtime work remain provenance, not current component placement.

No runtime migration.

## 13. Active-source coverage result

A broad source search over the legacy repository exposed the active `src/reht` surfaces above, including issuance, RACS codec/validation/verification/trust, normative clearance, post-boundary handoff, cancellation, workspace clearance, security attestation and sustainability profile.

This reconciliation establishes **zero `MIGRATE_RUNTIME` items** among those inspected active source families.

The result does not authorize deletion. Any file not covered by the active-source/domain/research classes above remains `NOT_ESTABLISHED` until lifecycle review confirms it is history, generated material, test support or otherwise non-unique.

## 14. Current migration matrix

| Legacy surface | Result | Target / action |
|---|---|---|
| package/manifest ownership | `REJECT_CONFLICTING_OR_STALE` | preserve history only |
| Draft 0.1 runtime specification | `REJECT_CONFLICTING_OR_STALE` | standards concepts only via `reht-standard` governance |
| RACS v0.2 issuer/boundary/signing stack | `REJECT_CONFLICTING_OR_STALE` | use `Racs` contracts; no REHT re-ownership |
| RACS codec/schema/trust/verification utilities | `REJECT_CONFLICTING_OR_STALE` | use canonical RACS/trust owners |
| Governed Workspace authorization | `HISTORICAL_ONLY` | already represented in canonical `valo-reht` |
| normative VAIG handoff / non-execution determination | `REJECT_CONFLICTING_OR_STALE` | VAIG evidence + RACS outcome semantics; no REHT outcome expansion |
| post-boundary handoff receipt | `REJECT_CONFLICTING_OR_STALE` | RACS/Gateway/Veritas if a portable binding is required |
| cancellation authorization artifact | `REJECT_CONFLICTING_OR_STALE` | express cancellation as exact action; RACS/workflow/Gateway binding if required |
| Agent Skills binding | `NOT_ESTABLISHED` | no migration without a current contract requirement |
| external security verifier profile | `MOVE_STANDARD_PROPOSAL` | standards/evidence/adapter review |
| sustainability action profile | `MOVE_DOMAIN_PROFILE` | domain pack/profile if retained |
| research/manuscripts/evidence/claims | `MOVE_RESEARCH_EVIDENCE` / `HISTORICAL_ONLY` | research/publication/history |

## 15. Architectural result

The inspected legacy repository does not establish a second runtime authorization property that requires an independent REHT implementation.

Current ownership remains:

```text
fresh exact-action authorization -> nsolland/valo-reht
RACS binding contracts           -> nsolland/Racs
REHT public standard/conformance -> nsolland/reht-standard
external evidence adapters       -> bounded adapter/evidence owners
domain action profiles           -> domain pack/profile owners
research/publication             -> research/publication owners
```

The legacy repository therefore moves toward historical/reference state after remaining non-source lifecycle material is confirmed and independent review accepts the reconciliation.

## Invariants

`ONE_RUNTIME_AUTHORIZATION_OWNER`

`REHT_AUTHORIZATION != RACS_CONTRACT_OWNERSHIP`

`DOMAIN_PROFILE != AUTHORIZATION_KERNEL`

`EVIDENCE_PRODUCER != AUTHORITY_SOURCE`

`CANCELLATION != PARALLEL_AUTHORIZATION_PATH`

`HISTORICAL_IMPLEMENTATION != CURRENT_CANON`

`UNCLASSIFIED != SAFE_TO_DELETE`
