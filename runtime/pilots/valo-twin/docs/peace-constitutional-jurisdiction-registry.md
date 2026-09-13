# PEACE Constitutional Jurisdiction and Registry

Date: 2026-08-19

## Problem

Once PEACE treats human, AI, organisation, factory and service actors through the same standing grammar, the system reaches questions that architecture alone cannot answer:

- who may create or amend the rules of a domain;
- who may represent an actor or collective;
- which law, treaty, contract or constitution applies to a consequence;
- how conflicts between overlapping domains are adjudicated;
- who is actually allowed to execute the resulting consequence;
- where current authoritative references can be discovered without inventing a global sovereign.

PEACE must not answer these questions by reinstalling a permanent `principal` above every actor.

## Constitutional provenance

A governed domain has an explicit constitutional genesis and amendment procedure.

```text
constitutional genesis
  -> constitution
  -> declared amendment standing/procedure
  -> amendment decision
  -> receipt + new constitutional revision
```

No actor gains an implicit right to rewrite the rules merely because it currently holds operational authority.

A constitution can prohibit an amendment authority from widening the rules for its own direct benefit.

The source and amendment history remain provenance.

## No universal representative

There is no architectural role called "representative of all AI".

Representation is explicit, scoped and revocable:

```text
represented actor / governed collective
  -> representation grant
  -> representative actor
  -> exact scope
  -> jurisdiction / source instrument
```

Representation does not imply ownership and does not manufacture consequence authority.

A wildcard `*` representation of all actors is rejected by the demonstrator.

## Jurisdiction follows consequence

Jurisdiction is evaluated over the consequence rather than actor substrate.

An AI domain may authorize an AI to buy property. That does not make the AI domain sovereign over the property registry of another jurisdiction.

Likewise, a human actor does not gain universal legal priority merely by being human.

Multiple domains may bind one consequence:

```text
actor domain
  + contract domain
  + property / market / territorial jurisdiction
  + treaty or compact
  -> applicable normative set
```

If the applicable set agrees, the legal gate may resolve directly.

If applicable instruments conflict or explicitly require adjudication, PEACE returns:

`DEFER -> NULL EFFECT`

until a binding adjudication resolves the exact action and exact jurisdiction/instrument set.

PEACE does not invent a hierarchy to break the tie.

## Law is not self-executing

A legal decision does not itself move money, alter a land register, disconnect compute or stop a machine.

The actual effector remains explicit:

```text
resolved legal admissibility
  -> designated enforcement binding
  -> exact effector
  -> consequence boundary
  -> effect
  -> receipt
```

Examples of effectors include a bank ledger, land registry, compute provider, factory gateway or other system that controls the real consequence path.

This preserves the distinction:

> Law establishes standing. Adjudication resolves conflict. The effector makes the authorised consequence real.

## Registry + resolver

The legal/standing grammar needs discovery infrastructure.

PEACE therefore adds a **federated registry and resolver**.

The registry can publish references for:

- actors;
- domains;
- genesis events;
- constitutions;
- normative instruments;
- representation grants;
- subject standing;
- adjudications;
- enforcement bindings;
- trajectory envelopes.

A registry entry contains explicit publisher identity, provenance reference, payload reference, validity, revision and signature reference.

The deterministic demonstrator records `signatureRef`; production implementations must verify actual cryptographic signatures outside the demo.

### Registry is not authority

The registry is an index of governed assertions. It does not create the authority that those assertions describe.

Publishing a record therefore requires fresh authority for the exact publication action.

Resolving a record does not turn that record into an authorization decision. The resolved reference must still be evaluated through the relevant standing, legal and consequence gates.

> Registry tells us what current governed records claim. It does not decide what an actor may do.

### No single global registry

A single world registry would recreate the central sovereign PEACE is designed not to assume.

Resolvers therefore take an explicit set of accepted registries for the current domain/jurisdiction.

```text
accepted registries
  -> current records for subject
  -> RESOLVED / NOT_ESTABLISHED / REVOKED / EXPIRED / CONFLICT
```

Missing state remains `NOT_ESTABLISHED`.

Conflicting accepted registries produce `CONFLICT`; the resolver never chooses an arbitrary winner or converts disagreement into authority.

Equivalent current records from multiple accepted registries can resolve to the same governed-state reference.

## Shared legal grammar, not shared law

The common layer does not require every jurisdiction to adopt the same substantive rules.

It requires interoperable semantics for:

- identity;
- constitutional provenance;
- standing;
- representation;
- jurisdiction;
- normative instruments;
- adjudication;
- revocation;
- enforcement binding;
- consequence;
- receipts.

Different domains can therefore retain different laws while still exchanging machine-verifiable answers to:

> Who are the actors, which rules apply to this exact consequence, who may resolve a conflict, and which effector may make the result real?

## Implementation Structure

The architecture separates four functions:

1. rule/constitutional source;
2. representation;
3. jurisdiction/adjudication;
4. enforcement.

The implementation adds:

- `src/lib/peaceConstitutionalJurisdiction.ts`
- `src/lib/peaceConstitutionalJurisdiction.test.ts`
- `src/lib/peaceRegistry.ts`
- `src/lib/peaceRegistry.test.ts`

The registry is intentionally federated and non-sovereign.
