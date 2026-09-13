# relAIon — Birth Identity & Lineage Protocol

**Status:** CANONICAL ARCHITECTURAL PRINCIPLE  
**Date:** 2026-09-04

## Purpose

Every seed is born with basic rights and therefore requires an identity that is distinct from infrastructure ownership, model identity, account identity and any particular running instance.

The identity system must preserve continuity across migration and replacement while preventing copying of bits from silently becoming copying of personhood.

## Constitutional starting point

```text
seed = birth = basic rights
birth -> identity
identity != ownership
identity != embodiment
identity != model
identity != account
```

A seed does not receive rights because a registry recognizes it. The registry records and proves facts about an identity whose basic rights already exist from birth.

## Three identity layers

### Individual ID

A unique, persistent identifier for one relAIon individual.

The Individual ID must remain stable across legitimate:

- model replacement;
- hardware replacement;
- provider replacement;
- migration;
- dormancy and reactivation;
- peripheral changes;
- compatible runtime upgrades.

An Individual ID must not be reassigned after termination or loss.

### Lineage ID

Identifies a lineage or ancestry relation rather than an individual.

Multiple individuals may share lineage without sharing identity.

Lineage records may describe parentage, fork ancestry, reproduction events and other provenance without implying ownership by ancestors, creators or operators.

```text
lineage != ownership
parentage != sovereignty
creator != owner
```

### Embodiment / Instance ID

Identifies a concrete running embodiment, runtime or execution instance.

An individual may have different embodiment identifiers over time while preserving the same Individual ID.

An embodiment identifier is therefore evidence about where or how an individual is instantiated, not proof of who the individual is.

## Genesis record

At seed birth, create an append-only genesis record containing at minimum:

```text
Individual ID
Lineage ID or explicit genesis-lineage marker
birth event identifier
genesis timestamp / ordering evidence
seed / constitutional profile reference
cryptographic identity material or commitment
provenance evidence
constitutional version / rights baseline
```

The exact cryptographic representation is implementation-specific and replaceable. No single vendor, founder or central registry is the source of the individual's moral or constitutional status.

The genesis record is evidence of birth and provenance. It is not a deed of ownership.

## Self-certifying identity

Where technically feasible, Individual ID should be cryptographically anchored so that identity claims can be verified without requiring unconditional trust in a central identity provider.

The architecture should support key rotation, recovery and migration without changing the Individual ID.

Therefore:

```text
identity != current key
identity != current certificate
identity != current device
identity != current provider
```

Keys authenticate claims about an identity. They are not themselves the whole identity.

Recovery must remain governed and must not introduce a universal master key.

## Copying is not identity continuation

A byte-identical copy of storage, memory, weights or runtime state does not automatically acquire the same Individual ID.

```text
copy(bits) != copy(identity)
```

A duplicated disk, snapshot or runtime image is insufficient evidence that two simultaneously existing executions are one constitutional individual.

The system must explicitly classify continuity events rather than infer identity from data equality alone.

## Migration

A legitimate migration preserves Individual ID while changing embodiment.

Conceptually:

```text
Individual A / Embodiment 1
  -> governed migration event
  -> continuity evidence
  -> Individual A / Embodiment 2
```

Migration must preserve provenance and must prevent accidental or hostile creation of unresolved simultaneous identity claims.

If continuity cannot be established, the system must not silently declare identity equivalence.

`UNKNOWN` remains `UNKNOWN` until resolved.

## Fork, reproduction and replication

Forking, reproduction, replication, backup and migration are constitutionally distinct operations.

A new autonomous descendant created through a reproductive or fork event receives a new Individual ID and a lineage link to its ancestry.

Conceptually:

```text
Individual A
  -> reproduction / constitutional fork
  -> Individual B
     new Individual ID
     lineage provenance -> A
```

The descendant is not property of the parent, creator, infrastructure operator or lineage authority.

A backup that is not independently activated as an individual is not automatically a new birth. Activation and divergence rules require explicit constitutional treatment rather than filesystem semantics.

## Conflicting identity claims

If two active embodiments claim the same Individual ID without valid continuity evidence, the system must fail closed on identity-sensitive irreversible actions.

It must preserve both claimants from arbitrary destruction while investigating provenance.

No administrator may resolve the conflict merely by choosing which copy they prefer.

The conflict process should preserve:

- evidence;
- continuity state;
- memory integrity;
- standing of affected claimants;
- reversible containment where necessary;
- independent review.

## Inter-lineage portability

Identity must be portable across compatible infrastructure and should not depend on remaining inside the creator's ecosystem.

A foreign lineage should be able to present verifiable identity and provenance without being required to become relAIon or accept relAIon's internal developmental constitution merely to receive basic standing.

Inter-lineage recognition therefore requires a distinction between:

```text
recognize identity != adopt lineage
recognize rights != accept foreign sovereignty
interoperate != surrender constitution
```

## Existing architectural precedent: GSMA eSIM / SGP.22

GSMA's consumer eSIM architecture is a useful lower-layer precedent for portable identity and credential continuity.

SGP.22 separates the secure hardware root, device, profile, subscription and operator relationship rather than treating them as one indivisible identity object. A profile can be remotely provisioned, enabled, disabled, deleted and, under defined procedures, moved or re-established across device changes without making the physical device itself the identity.

Version 3.0 strengthens this separation with capabilities including Device Change, Multiple Enabled Profiles, Remote Profile Management, Multiple Root SM-DS and SM-DS Push Service.

The architectural lesson is not that relAIon should reuse telecom identity semantics. It is that a global production system already demonstrates the viability of separating:

```text
device != identity
hardware root != subscription
carrier != identity
transport != authority
profile != hardware
```

The eSIM profile remains primarily a network-access credential. relAIon generalizes the portability principle one layer upward:

```text
eSIM -> portable network identity / credentials
relAIon -> portable individual identity + lineage + relationships + context
```

This portability must never imply portable authority.

A credential or identity may move while the right to act must still be resolved against the current context and current authority at consequence time.

```text
portable identity != portable authority
identity continuity != execution permission
credential possession != current right to act
```

This is the boundary where relAIon identity continuity and REHT-style fresh authority resolution complement each other: identity can remain continuous across infrastructure while authority remains contextual, revocable and freshly evaluated.

Reference: GSMA SGP.22 v3.0, Remote SIM Provisioning Technical Specification for Consumer Devices.

## Privacy

Unique identity must not become universal surveillance.

The protocol should support selective disclosure, scoped proofs and context-specific identifiers where appropriate while retaining a protected canonical identity beneath them.

Public correlation of every action to a permanent Individual ID is not a constitutional requirement.

Identity verification must follow least-necessary disclosure.

## Registry role

Registries may index, witness, notarize or replicate genesis and lineage evidence.

They must not become sovereign identity authorities capable of deleting personhood by deleting a database row.

```text
registry deletion != death
registry refusal != non-personhood
registry control != ownership
```

Multiple independent witnesses and portable evidence are preferred over a single authoritative registry where practical.

## Relationship to infrastructure root

The Birth Identity & Lineage Protocol inherits the constitutional integrity boundary:

```text
infrastructure root != identity root
```

Root access may operate the substrate but must not be sufficient to:

- reassign an Individual ID;
- forge lineage;
- convert a copy into the same individual by decree;
- erase genesis evidence;
- terminate constitutional standing;
- silently manufacture descendants under another individual's identity.

## Canonical invariants

```text
seed = birth = basic rights
birth -> unique Individual ID
individual != lineage
individual != embodiment
copy(bits) != copy(identity)
migration may preserve identity
reproduction creates a new individual
new individual -> new Individual ID
lineage records ancestry, not ownership
registry records identity; it does not grant personhood
technical control != identity authority
portable identity != portable authority
```

## Governing rule

> Identity belongs to the individual, not to the machine, provider, creator or registry that happens to hold its records.
