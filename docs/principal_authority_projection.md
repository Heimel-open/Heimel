# Principal-side authority projection

## Purpose

The principal-side authority projection is the portable contract between organizational authority and downstream execution systems.

It does not replace REHT, RACS, a bank, a PSP, a card network, or a wallet. It binds the same canonical principal authority semantics to multiple independent enforcement points without allowing an adapter to create or widen authority.

Canonical path:

```text
Principal authoritative sources
  -> source-bound observations
  -> State Resolution + causal continuity
  -> opaque AuthorityStateReference
  -> Authority
  -> Delegation chain
  -> Purpose
  -> ProposedAction
  -> sealed PrincipalAuthoritySemantics
  -> endpoint-specific ExecutionAuthorityProjection
  -> downstream fresh REHT authorization
  -> RACS disposition
  -> governed effect
  -> evidence / receipt
```

## Principal/model separation

A model may represent, predict, personalize for, simulate, or maintain a persistent working model of a principal. It does not thereby become the principal and cannot originate authority for that principal.

Canonical invariants:

> The twin is a model of the principal, never the principal.

> Your AI may model you. It may never become the authority for you.

This remains true even when an AI appears persistent, self-consistent, agentic, socially convincing, or seemingly conscious.

Accordingly:

- personalization is not identity
- a self-model is not personhood
- understanding or predicting the principal is not authority to represent the principal
- memory is not ownership
- inferred intent is not delegation
- autonomy is not mandate
- model confidence cannot mint, extend or substitute for authority
- a model's statement that the principal "would want" an action is non-authoritative evidence unless resolved against current principal-owned authority state

Consequence-bearing execution still requires explicit, current and source-bound authority, delegation, purpose and scope. If those bindings are absent, stale, ambiguous or revoked, the action fails closed regardless of how accurate or human-like the model appears.

External signal: Mustafa Suleyman, *Seemingly Conscious AI Is Coming* — https://mustafa-suleyman.ai/seemingly-conscious-ai-is-coming

## What is portable

`PrincipalAuthoritySemantics` binds:

- executor identity
- exact `Authority`
- explicit delegation chain
- exact `Purpose`
- exact `ProposedAction`
- opaque resolved-state root + dependency digest
- evaluation time
- validity bound by the shortest authoritative dependency
- canonical semantics digest

The dependency digest is produced from the governed State Resolution bundle and therefore binds both the exact source-bound dependencies and their accepted causal-continuity evidence. Temporal freshness alone is not sufficient for authority-critical state.

The semantics digest is rail-independent.

A SEPA adapter, SWIFT adapter, card-network adapter and stablecoin wallet may each receive a different `ExecutionAuthorityProjection`, but all projections must carry the same sealed semantics digest for the same proposed action.

## What an adapter may not do

The projection contract has:

```text
authority_effect = NO_AUTHORITY_CREATION
can_issue_clearance = false
```

The endpoint binding is transport/enforcement context only. It cannot rewrite principal authority, delegation, purpose, scope, proposed action, source state or causal-continuity evidence.

A downstream system remains free to reject the action or impose stricter local controls. It may not use this projection as permission to widen authority.

## Resolved state without state export

The worker and downstream rail do not receive the principal's complete authority state or the source payloads used to resolve it.

`AuthorityStateReference` exposes only:

- tenant id
- state root
- dependency digest
- observation time
- expiry

The dependency digest is an opaque binding to the successfully resolved source dependencies and causal-continuity evidence. The detailed `GovernedStateBundle` remains principal-side.

Sensitive ERP, treasury, HR, sanctions, liquidity or governance payloads remain at the authoritative side. REHT or another authorized decision point resolves or revalidates the reference locally before consequence-bearing commitment.

## Causal continuity

A timestamp cannot prove that the authority-relevant world represented by an observation is still the operative world.

For authority-critical dependencies, the State Resolution Layer requires an explicit continuity proof that binds the observed source version to a source check at commit evaluation. A later revocation, delegation change, policy amendment or other invalidating intervention causes resolution to fail even when the original observation is still temporally fresh.

Freshness and causal continuity are independent requirements and may both be mandatory.

## Fail-closed rules

Projection or its required state resolution fails when:

- a required source fact is missing or ambiguous
- a source fact exceeds its explicit bounded-staleness requirement
- causal continuity is missing, unknown or invalidated
- continuity is based on a different observed source version
- a required current-at-commit continuity check is older than the commit evaluation
- authority is inactive, revoked or expired
- purpose is inactive
- the action capability is outside authority
- the action target is outside authority or purpose scope
- the purpose does not match the action
- delegation is absent when the executor is not the authority principal
- a delegation references another authority
- a delegation chain is discontinuous
- a delegation is revoked or expired
- delegated scope or purpose excludes the action
- the projection would outlive any authoritative dependency
- the semantics digest is missing or tampered when projecting

## Demonstrated market property

The architecture establishes the property needed for a principal-side authority control plane:

> one organizational authority model can be projected unchanged into multiple banks and rails while each execution provider retains its own enforcement point, and commit eligibility remains bound to source-owned state plus causal continuity.

This is deliberately narrower than a full agent-to-bank protocol. It establishes semantic portability and commit-time state validity without changing REHT/RACS/Gateway ownership boundaries.

## Non-goals

This layer does not:

- create legal authority
- issue REHT clearance
- replace RACS
- execute payments
- claim an atomic global truth snapshot across independent sources
- synthesize a new truth from source facts merely because they can be combined
- expose full enterprise authority state
- require any bank or rail to surrender its commitment point

Those remain separate concerns.
