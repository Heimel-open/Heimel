# PEACE Protocol v0

**Personal Execution, Authority & Compute Environment**  
**Your Sovereign State.**

## 1. Status and scope

This document defines the public, language-neutral interoperability semantics for PEACE v0.

PEACE does not prescribe a programming language, operating system, model provider, database, device class, credential scheme, cryptographic library, compute provider, payment provider or internal product topology.

Normative words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are requirements of this draft.

The public protocol surface is intentionally limited to observable semantics required for independent implementation and conformance.

## 2. Core principle

> **Everything can be routed except sovereignty.**

A person or organisation may replace models, agents, devices, credentials, services, clouds, compute providers, routers and settlement rails without those replaceable components becoming the source of authority.

Capability, possession, routing, successful authentication, computation or evidence do not by themselves create authority to act.

## 3. Constitutional invariants

A conformant implementation MUST preserve the following observable semantics:

1. **ACTOR_IS_AUTHORITY_ROOT** — the logical protected actor/domain is the root of authority. A credential, key, device, provider, model, runtime, storage location or compute node MUST NOT become the authority root merely by representing, authenticating or serving that actor.
2. **CONTINUITY_ACROSS_REPLACEMENT** — replacement or loss of a replaceable artifact MUST NOT by itself replace the logical actor/domain or transfer its authority. Required admitted state, unresolved governed material, governance, evidence lineage and recovery semantics MUST remain attributable to the same logical actor/domain.
3. **CAPABILITY_NE_AUTHORITY** — capability, intelligence, possession of data, successful authentication, attestation, routing or computation MUST NOT create authority to act.
4. **CANDIDATE_NE_DECISION** — observation, inference, prediction, recommendation, plan or generated action is candidate material only.
5. **DISCLOSURE_IS_GOVERNED** — information leaving the protected domain MUST be bounded by purpose, destination and governed context.
6. **NO_DIRECT_EFFECT_PATH** — a replaceable worker, model, runtime or service MUST NOT turn its own output directly into a consequence-bearing effect.
7. **FRESH_AUTHORITY_AT_EFFECT** — a consequence requires authorization against current relevant state and current authority for the exact action immediately before effect.
8. **EVIDENCE_NE_STATE** — evidence records claims, observations, proposals, authorizations, attempts or outcomes. Evidence MUST NOT mutate authoritative state merely by existing, being signed or being tamper-evident.
9. **ROUTING_NE_AUTHORITY** — route or provider selection MAY affect capability or admissibility but MUST NOT create authority.
10. **IMPLEMENTATION_NE_PROTOCOL** — implementation language, runtime, transport, storage and cryptographic mechanism are replaceable and non-authoritative.
11. **AUTHORITY_OVER_ACTION_NE_AUTHORITY_OVER_ACTOR** — authorization for one action MUST NOT imply ownership or general authority over another actor.
12. **RECOVERY_NE_TRANSFER** — loss of access MAY permit recovery of control but MUST NOT permit a recovery provider to become or transfer the actor merely by performing recovery.
13. **REPLICA_NE_SOVEREIGN** — a replica MUST NOT become authoritative merely because it contains newer bytes.
14. **UNRESOLVED_IS_GOVERNED** — unresolved material is an explicit governed state. It MUST remain identifiable and consequential until an explicit governed admission decision resolves or rejects it.

These are interoperability semantics. Internal component names and product topology are not normative.

## 4. Required semantic separation

A conformant implementation MUST preserve separations equivalent to:

```text
authoritative state
  -> bounded disclosure/projection
  -> external or local work
  -> candidate
  -> current exact authorization
  -> effect / settlement
  -> evidence / outcome
  -> admission decision
  -> admitted state transition OR governed unresolved state
```

The following distinctions are normative:

```text
knowledge      != authority
proposal       != decision
authorization  != effect
evidence       != authoritative state
credential     != actor
compute route  != authority source
payment rail   != economic authority
implementation != protocol
unresolved     != rejected
unresolved     != implicit acceptance
```

## 5. Required logical objects

Implementations may use any internal representation but MUST be able to express semantics equivalent to:

- a logical protected actor/domain;
- current authoritative state and a deterministic state commitment/reference;
- current standing and authority/delegation/revocation state;
- a purpose- and destination-scoped governed disclosure/projection;
- a worker result represented as a candidate;
- an exact consequence action;
- a fresh authorization decision bound to that action and current relevant state/authority;
- an effect/outcome receipt or evidence event;
- an admission decision with outcome **ACCEPT**, **REJECT** or **UNRESOLVED**;
- a durable unresolved binding preserving candidate/referent identity and relevant provenance;
- a recovery representation sufficient to preserve actor/domain continuity;
- replication lineage sufficient to reject stale or divergent state transitions.

The public logical envelope is defined by `schemas/peace-envelope-v0.schema.json`.

## 6. Admission

Candidate information or evidence MUST receive an explicit admission outcome of **ACCEPT**, **REJECT** or **UNRESOLVED** before it can affect authoritative state when standing is required.

Persistence, signature validity, provider status, worker confidence, repetition or resubmission MUST NOT establish standing by themselves.

Only **ACCEPT** may produce an admitted transition that mutates authoritative state.

**UNRESOLVED** MUST remain durably associated with the relevant candidate/referent and provenance until an explicit later admission decision resolves or rejects it. It MUST NOT silently expire, become accepted by repetition or resubmission, or be merged with a conflicting unresolved interpretation without an explicit resolution process.

Where authorization depends on a fact or binding that remains materially unresolved, authorization MUST fail closed, defer, or require explicit resolution according to governing policy. It MUST NOT treat unresolved material as accepted merely to permit consequence.

## 7. Disclosure

A capability MUST receive no more governed information than its authorized purpose requires.

A disclosure authorization MUST be sufficiently bound to the protected actor/domain, destination, purpose, projection/scope and relevant validity conditions to prevent use outside the authorized disclosure.

Disclosure clearance MUST NOT itself authorize an external effect.

## 8. Proposal

A worker, model, service or other capability MAY calculate, infer, recommend or construct a candidate action.

A candidate is inert with respect to authoritative state and real-world consequence until the required governed decisions occur.

## 9. Authorization

Before consequence, the exact action MUST be evaluated against fresh current governed state and authority.

Where applicable, authorization MUST bind or verify:

- protected actor/domain;
- acting delegate/capability;
- current standing;
- delegation scope and revocation state;
- purpose and scope;
- exact action semantics and parameters;
- current relevant state commitment/version;
- current authority state;
- validity/freshness conditions;
- required admissibility/evidence conditions.

A prior disclosure grant, old authorization, model confidence, route decision, credential possession, compute allocation or payment capability MUST NOT substitute for the fresh consequence-time check.

## 10. Effect and settlement

Only the exact authorized consequence MAY be attempted.

If current authority, state, standing, revocation, purpose, scope, exact-action binding or required evidence/admissibility no longer satisfies authorization, the result MUST be null effect / fail closed.

Settlement is a consequence and follows the same rule. Availability of a payment rail or valid payment credentials MUST NOT bypass current authorization for the exact economic action.

## 11. Evidence

Effect attempts and outcomes SHOULD produce evidence sufficient to correlate the candidate, authorization, exact effect attempt and observed result.

Cryptographic integrity, signer authority, policy meaning, artifact resolution and external truth are distinct verification questions.

Evidence MUST NOT acquire authoritative standing merely because it is signed or tamper-evident.

## 12. Replication

Replication MUST preserve admitted state transitions, governed unresolved records and lineage semantics rather than relying on last-write-wins for authoritative state.

A replica MUST NOT become sovereign merely because it is newest.

Conflicting lineage MUST fail closed to explicit resolution, re-authorization or rejection. Silent merge of conflicting authoritative lineage is non-conformant.

## 13. Recovery

Recovery MUST preserve the same logical actor/domain while allowing credentials, keys, devices, runtimes, storage and providers to rotate or be replaced.

A recovery provider MUST NOT unilaterally become or transfer the actor merely because it can restore access.

Recovery mechanisms SHOULD support independent evidence, compartmentalization, revocation of lost credentials and auditable evidence of the recovery transition.

## 14. Routing and capability

PEACE does not prescribe a model router, compute scheduler, capability factory, service provider or payment processor.

Routing MAY consider capability, cost, latency, energy, locality, trust, privacy, availability or quality. Route selection remains subordinate to disclosure, standing, authority and consequence constraints.

A provider or capability MUST NOT derive sovereign standing, delegation or execution authority merely from provider credentials, technical permissions, route selection or prior successful execution.

## 15. Relationship to reht and other contracts

PEACE is implementation independent.

A portable agent/work contract MAY express governed intent inside a PEACE flow. A consequence gate such as `reht` MAY implement the fresh exact consequence-time authorization boundary.

Neither is a mandatory dependency. Equivalent independent components MAY be used when the observable PEACE semantics and conformance requirements are preserved.

## 16. Canonical digest encoding v0

Cross-language conformance artifacts use this encoding before SHA-256:

1. UTF-8 JSON.
2. Object keys sorted lexicographically by Unicode code point.
3. No insignificant whitespace.
4. Array order preserved.
5. Standard JSON string escaping.
6. `true`, `false`, and `null` for booleans/null.
7. No floating-point values in canonical digest objects for v0; integers are permitted.

`digest(x) = "sha256:" + lowercase_hex(SHA256(canonical_json(x)))`

## 17. Conformance

A claimed PEACE v0 core implementation MUST demonstrate the mandatory semantic vectors in `conformance/conformance-v0.json`, including at least:

- valid exact-action authorization permits the effect;
- revocation before effect prevents effect;
- stale relevant state invalidates prior authorization;
- action drift prevents effect;
- worker output cannot bypass the effect boundary;
- candidate material is not a decision;
- routing does not create authority;
- settlement cannot bypass fresh authority;
- evidence does not mutate authoritative state without admission;
- unresolved material persists and cannot become accepted through timeout, repetition or resubmission;
- materially unresolved required bindings prevent authorization from treating them as admitted;
- conflicting unresolved interpretations do not silently merge;
- replicas cannot self-promote to sovereignty;
- conflicting authoritative lineage does not silently merge;
- recovery preserves the same logical actor/domain and does not transfer authority to a recovery provider.

Conformance is an observable interoperability claim. It is not a certification of security, legal compliance, truth, policy quality or implementation fitness beyond the declared profile.

## 18. Open protocol boundary

PEACE is intended to be independently implementable and royalty-free for interoperability.

Commercial implementations, managed control planes, certification, assurance, recovery services, registries, adapters and support MAY be proprietary.

Research derivations, experimental capability composition, model-specific state transfer, routing intelligence and internal implementation architecture are outside this public protocol specification unless deliberately standardized in a later reviewed release.
