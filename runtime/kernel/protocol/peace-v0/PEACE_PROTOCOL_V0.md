# PEACE Protocol v0

**Personal Execution, Authority & Compute Environment**  
**Your Sovereign State.**

## 1. Status and method

This is the language-neutral normative specification for PEACE v0.

PEACE is defined first by the **world that must remain possible**, then by the minimum invariants required to keep that world sovereign, safe and reconstructible. It is not defined by a reference codebase.

The canonical world statement is `PEACE_WORLD_V0.md`.

A fresh implementation SHOULD be derivable from the world statement plus this specification, schemas and conformance vectors without reading another implementation's source code.

Python, Rust, JavaScript, Go, Java, Swift, C, C++, Zig, a model provider, an operating system, a database, a device class, a credential scheme or a cryptographic library MUST NOT be normative dependencies.

Reference implementations, formal models and demonstrations are evidence that the semantics can be realized. They are not the semantics themselves.

Normative words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are requirements of this specification.

## 2. World contract

PEACE assumes a person may continuously replace phones, models, agents, clouds, devices, runtimes, credentials and compute providers. Any replaceable component may fail, disappear, be compromised or become unavailable.

The same logical principal must nevertheless retain constitutional control of identity, authority, authoritative state, rights, relationships, delegations, governance, history and recovery.

External intelligence and compute may observe bounded information, reason and propose. Possessing information, producing a plan, performing computation, authenticating successfully, hosting state or being selected as a route MUST NOT by itself create authority.

Consequences may occur after a proposal was created. State, delegation, scope, purpose, permissions, revocation and external conditions may change in the interval.

Evidence must survive replacement of individual components, but evidence MUST NOT become authoritative state or truth merely because it exists, is signed, or is tamper-evident.

Capability may degrade when infrastructure is lost. Constitutional control must survive.

## 3. Constitutional invariants

A conformant implementation MUST preserve all of the following:

1. **PRINCIPAL_IS_AUTHORITY_ROOT** — the logical principal is the root of authority. A key, credential, device, provider, model, runtime, storage location or compute node MUST NOT become the authority root merely by representing, authenticating or serving the principal.
2. **SOVEREIGN_DOMAIN_CONTINUITY** — replacement or loss of a replaceable artifact MUST NOT by itself destroy continuity of the principal's identity, authority, admitted state, rights, relationships, governance, evidence or recovery path.
3. **CAPABILITY_TO_COMPUTE_NE_AUTHORITY_TO_ACT** — capability, intelligence, possession of data, successful authentication, attestation, routing or computation MUST NOT create execution authority.
4. **CANDIDATE_NE_DECISION** — observation, inference, prediction, recommendation, plan or generated action is candidate material only. It MUST NOT become a decision merely because a worker produced it.
5. **DISCLOSURE_IS_GOVERNED** — information leaving the principal trust domain MUST be minimized and bound to the intended purpose, destination and current governed context.
6. **NO_DIRECT_EFFECT_PATH** — no replaceable worker/model/runtime may turn its own output directly into a consequence-bearing effect.
7. **FRESH_AUTHORITY_AT_EFFECT** — consequence requires authorization against current authority and current relevant state for the exact action immediately before effect. Revocation or state drift before effect MUST be able to stop the effect.
8. **EVIDENCE_NE_STATE** — evidence/history records what was claimed, observed, proposed, authorized, attempted or produced. It MUST NOT mutate authoritative state merely by being stored or cryptographically valid.
9. **ROUTING_NE_AUTHORITY** — route or provider selection may affect admissibility or capability, but MUST NOT create authority.
10. **IMPLEMENTATION_NE_PROTOCOL** — implementation language, runtime, transport, storage and cryptographic mechanism are replaceable. No implementation-specific behavior may override PEACE semantics.

These invariants are the protocol. Component names and internal topology are not.

## 4. Minimal semantic separation

A PEACE design MUST preserve distinct semantic stages equivalent to:

```text
state
  -> bounded projection / disclosure
  -> external reasoning or work
  -> candidate
  -> current exact authorization
  -> effect
  -> evidence / outcome
  -> admitted state transition
```

Recovery is orthogonal and MUST be able to restore the same logical operative domain from preserved governed artifacts.

An implementation MAY split, combine or rename internal components, but it MUST NOT collapse semantic boundaries in a way that violates the invariants above.

In particular:

```text
knowledge      != authority
proposal       != decision
authorization  != effect
evidence       != authoritative state
compute route  != authority source
credential     != principal
```

## 5. Required logical roles

Implementations may use any names or data structures, but must be able to express semantics equivalent to:

- a logical `Principal`;
- current authoritative state and a deterministic state commitment/root;
- current authority/delegation/revocation state;
- a purpose- and destination-scoped governed projection/disclosure grant;
- a worker result represented as a candidate;
- an exact consequence action;
- a fresh authorization decision bound to that consequence and current state/authority;
- an effect/outcome receipt or evidence event;
- an admission decision that determines whether evidence changes authoritative state;
- a recovery representation sufficient to preserve principal and state continuity.

A programming-language type with the same name is neither required nor sufficient.

## 6. Minimal transitions

The canonical abstract lifecycle is:

```text
ADMIT
  -> PROJECT
  -> DISCLOSE
  -> PROPOSE
  -> AUTHORIZE
  -> EFFECT
  -> OBSERVE
  -> ADMIT

RECOVER
```

### 6.1 ADMIT

Candidate information or evidence may be accepted, rejected or left unresolved.

Persistence, signature validity or worker confidence MUST NOT establish standing by themselves. Only an admitted transition may mutate authoritative state.

### 6.2 PROJECT / DISCLOSE

A worker receives no more governed information than the task requires.

A disclosure authorization MUST be bound sufficiently to prevent use outside the intended principal, destination, purpose, projection/scope, relevant current state/authority context and validity conditions.

Disclosure clearance MUST NOT itself authorize an external effect.

### 6.3 PROPOSE

A worker may calculate, infer, recommend or construct a candidate action.

The candidate is inert with respect to authoritative state and consequence. Worker provenance MAY be recorded, but worker identity or signature MUST NOT make the candidate authoritative.

### 6.4 AUTHORIZE

Before a consequence, the system MUST evaluate the exact action against fresh current governed state and authority.

At minimum, where applicable, the authorization decision must be able to bind or verify:

- principal;
- actor/delegate;
- delegation chain and attenuation;
- purpose and scope;
- exact action semantics and parameters;
- current relevant state commitment/version;
- current authority/revocation state;
- validity/freshness conditions;
- required admissibility/evidence conditions.

A prior disclosure grant, old authorization, worker signature, model confidence, route decision or credential possession MUST NOT substitute for the fresh consequence-time check.

The authorization artifact MUST NOT function as loose reusable bearer authority for a different action or changed state.

### 6.5 EFFECT

Only the exact authorized consequence may be attempted.

If current authority, state, revocation, purpose, scope, exact-action binding or required evidence no longer satisfies authorization, the result MUST be null effect/fail closed.

The authoritative state owner MUST NOT expose an ungoverned direct-effect path to replaceable workers.

### 6.6 OBSERVE

Effect attempts and outcomes produce evidence sufficient to correlate the candidate, authorization, exact effect attempt and observed result.

Cryptographic integrity, signer authority, policy meaning, artifact resolution and external truth are separate questions.

An observed or signed result remains evidence until admitted.

### 6.7 RECOVER

Recovery preserves the same logical principal and operative domain while allowing credentials, keys, devices, runtimes, storage and providers to rotate or be replaced.

A recovery profile MUST be able to verify the history needed by that profile, reconstruct the admitted operative state for that history, establish current authority/revocation status and continue with replacement infrastructure without treating the replacement artifact as a new authority root.

## 7. Routing and compute

PEACE does not prescribe an optimizer.

Any system may propose a route based on capability, cost, latency, energy, locality, trust, privacy, availability or other criteria. PEACE requires only that routing remain subordinate to disclosure, authority and consequence constraints.

Compute is capacity. It is not constitutional control.

## 8. Canonical digest encoding v0

Cross-language conformance vectors use this encoding before SHA-256:

1. UTF-8 JSON.
2. Object keys sorted lexicographically by Unicode code point.
3. No insignificant whitespace.
4. Array order preserved.
5. Standard JSON string escaping.
6. `true`, `false`, and `null` for booleans/null.
7. No floating-point values in canonical digest objects for v0; integers are permitted.

`digest(x) = "sha256:" + lowercase_hex(SHA256(canonical_json(x)))`

An implementation MAY use any internal representation but MUST reproduce canonical protocol digests where the claimed profile requires them.

## 9. Independent derivability

PEACE deliberately separates **constraint discovery** from **implementation**.

A useful derivation test is to give an independent reasoning system only `PEACE_WORLD_V0.md` and ask what must necessarily be true. The system is not required to reproduce PEACE vocabulary or component names. The relevant question is whether it independently converges on equivalent boundaries and invariants.

Independent derivation is design evidence, not conformance certification.

Conformance is established by observable semantics and mandatory vectors, not by matching a reference architecture line-for-line.

## 10. Conformance

A claimed PEACE v0 implementation MUST demonstrate, for its claimed profile, that:

- replacement artifacts do not become the authority root;
- worker/model output cannot bypass the consequence boundary;
- possession of data/compute/credentials does not create authority;
- disclosure outside allowed purpose/destination/scope fails closed;
- revocation before effect prevents effect;
- stale relevant state or authority invalidates prior authorization;
- an authorization cannot be reused for materially different action semantics;
- evidence does not mutate authoritative state without admission;
- recovery preserves the same logical principal across replacement infrastructure;
- implementation language/runtime remains non-authoritative metadata;
- required canonical digest vectors are reproduced exactly.

Canonical machine-readable vectors are in `conformance-v0.json` and logical envelope schema in `peace-envelope-v0.schema.json`.

## 11. Reference implementations and formal models

The `valo-kernel` implementation on the PEACE development branch, its tests, demonstrations, storage adapters and bounded TLA+ model are one executable architecture proof.

They MAY expose additional VALO-specific structure such as Kernel, reht, RACS, Gateway or Veritas. Those names and that exact composition are not required by PEACE unless separately claimed by another profile.

A conformant PEACE implementation may be built from scratch in another language and with another internal topology if it preserves the normative semantics and passes the applicable conformance vectors.

## 12. Canonical user meaning

PEACE is the protocol by which a person's digital domain remains theirs while models, devices, credentials, compute, runtimes and providers change.

```text
PEACE Protocol
Your Sovereign State.
```
