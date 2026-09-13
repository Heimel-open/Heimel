# State Resolution and Causal Continuity

## Purpose

The State Resolution Layer determines whether the authoritative facts required for a consequence-bearing decision are sufficiently known, source-valid and causally continuous for commit-time evaluation.

It does not create truth, authority or clearance.

Canonical path:

```text
authoritative sources
  -> source adapters
  -> source-bound observations
  -> causal continuity proofs
  -> State Resolution Layer
  -> GovernedStateBundle
  -> opaque AuthorityStateReference
  -> Authority / Delegation / Purpose
  -> REHT
  -> RACS
  -> governed effect
  -> receipt / evidence
```

## Source ownership

SAP remains authoritative for SAP facts. A bank remains authoritative for bank facts. IAM remains authoritative for identity and delegation facts. The resolver preserves source identity, fact identity, source version, provenance and value digest.

The resolver must not convert several source facts into a new canonical fact merely because they can be combined arithmetically or semantically.

For example, if SAP reports a budget and a bank reports settled spend, both remain separate source-bound facts. Any derived capacity calculation requires an explicit deterministic contract outside source resolution.

## Time is necessary but not sufficient

A recent timestamp does not establish that the world represented by an observation is still authority-valid.

A fact may be temporally fresh while a later revocation, delegation change, policy amendment, reservation, settlement or other authority-relevant intervention has causally invalidated the decision basis.

For authority-critical requirements, causal continuity is therefore mandatory.

Each continuity proof binds:

- source and fact identity
- observed source version
- source version checked at commit evaluation
- continuity status
- commit-time check instant
- explicit validity bound
- proof reference
- invalidating intervention references when applicable
- canonical proof digest

`CONTINUOUS` is the only admissible status. `INVALIDATED`, `UNKNOWN`, a missing proof, a version mismatch, an expired proof or a proof not checked at the required commit evaluation fails closed.

## Freshness remains independent

Causal continuity does not make arbitrarily old observations acceptable.

A requirement may separately declare `max_staleness_seconds`. The resolver enforces that bound even when causal continuity is proven.

This separates two questions:

1. Is the observation recent enough for this contract?
2. Has any authority-relevant intervention invalidated the observed basis?

Both may be required.

## No global truth-at-T claim

The State Resolution Layer does not claim to produce an atomic global snapshot across independent systems.

Its guarantee is narrower and auditable:

> These exact source-bound observations, versions and provenance references satisfied their declared freshness requirements and had verified causal continuity at this commit-time evaluation.

If a required source cannot provide the necessary evidence, the bundle is not produced.

## GovernedStateBundle

A successful bundle contains only the facts required by the declared resolution contract. It is sealed with:

- `continuity_digest` over the accepted continuity proofs
- `dependency_digest` over the exact source-bound dependencies plus the continuity digest, so the opaque dependency binding changes if accepted continuity evidence changes
- `bundle_digest` over the complete governed bundle
- the shortest explicit validity bound across observations, freshness limits and continuity proofs

The bundle has:

```text
authority_effect = NO_AUTHORITY_CREATION
can_issue_clearance = false
```

REHT remains the commit-time authority decision boundary.

## Deployment boundary

This layer is VALO code but should normally execute inside the principal's governed workspace or control plane, close to the authoritative sources and without requiring VALO to become a central data hub.

Adapters retrieve and translate source evidence. They do not own the represented facts and cannot widen authority.

## Fail-closed conditions

Resolution fails on at least:

- missing or ambiguous required source fact
- cross-tenant source evidence
- future observation
- expired source fact
- bounded-staleness violation
- missing or ambiguous continuity proof
- continuity proof/source version mismatch
- unsealed or tampered continuity proof
- `INVALIDATED` or `UNKNOWN` continuity
- continuity check older than a requirement marked current-at-commit
- expired continuity evidence
- absence of any explicit validity bound

Temporal freshness alone is never sufficient for an authority-critical fact.
