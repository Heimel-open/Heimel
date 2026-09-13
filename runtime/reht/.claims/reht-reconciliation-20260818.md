# Claim: reconcile nsolland/reht into canonical valo-reht

Owner: njal / ChatGPT
Date: 2026-08-18
Issue: #27
Canonical base SHA: df0c80de1be53e4380a0fdd6e2da6c7fb94736b8
Legacy/reference source SHA: nsolland/reht@8cbcd3b94f333a36ec5605b166049bf430b21a07
Branch: arch/reconcile-legacy-reht-20260818
PR: #28 (draft)

## Active delivery

Produce a file/contract-level reconciliation of `nsolland/reht` against canonical `nsolland/valo-reht`, migrate only unique semantically current runtime behavior that belongs in the canonical authorization boundary, and classify remaining material for standards, domain profiles, research/history or rejection.

## Classification outcomes

- MIGRATE_RUNTIME
- MOVE_STANDARD_PROPOSAL
- MOVE_DOMAIN_PROFILE
- MOVE_RESEARCH_EVIDENCE
- HISTORICAL_ONLY
- REJECT_CONFLICTING_OR_STALE
- NOT_ESTABLISHED

## Active-source result

Broad source inspection covered legacy issuance, RACS artifact/codec/schema/trust/verification utilities, Governed Workspace authorization, VAIG normative handoff, post-boundary handoff, cancellation authorization, Agent Skills binding, external security attestations and sustainability action profiles.

Established `MIGRATE_RUNTIME` items: **0**.

Key dispositions:

- package/manifest ownership: REJECT_CONFLICTING_OR_STALE
- Draft 0.1 runtime specification: REJECT_CONFLICTING_OR_STALE
- RACS issuance/codec/trust/verification: REJECT_CONFLICTING_OR_STALE
- Governed Workspace authorization: HISTORICAL_ONLY / already migrated
- normative VAIG handoff: REJECT_CONFLICTING_OR_STALE
- post-boundary handoff: REJECT_CONFLICTING_OR_STALE as REHT-owned behavior
- cancellation authorization: REJECT_CONFLICTING_OR_STALE as special path; cancellation remains expressible as an exact governed action
- Agent Skills binding: NOT_ESTABLISHED as irreducible REHT runtime requirement
- external security verifier semantics: MOVE_STANDARD_PROPOSAL / evidence-adapter review
- sustainability action profile: MOVE_DOMAIN_PROFILE
- research/evidence/claims: MOVE_RESEARCH_EVIDENCE / HISTORICAL_ONLY

No runtime code has been migrated or changed.

## Constraints

- `valo-reht` remains the sole runtime authorization owner.
- `reht-standard` remains the public standards/conformance owner.
- No semantic import solely because legacy code exists.
- No widening of runtime authority or outcome semantics.
- Preserve fail-closed, exact-action binding, fresh authority and single effect-path invariants.
- RACS transport/decision contracts are referenced, not re-owned.
- Research/publication material does not become runtime behavior.
- Unclassified material is not safe to delete.
- Independent review required before merge or lifecycle closure.

## Owned files

- `.claims/reht-reconciliation-20260818.md`
- `docs/architecture/REHT_LEGACY_RECONCILIATION_2026-08-18.md`
- runtime files only if an exact unique property is later established as MIGRATE_RUNTIME
- tests only for accepted runtime migration
