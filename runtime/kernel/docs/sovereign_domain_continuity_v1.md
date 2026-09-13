# PEACE Protocol — Sovereign Domain Continuity v1

**PEACE:** Personal Execution, Authority & Compute Environment  
**Canonical tagline:** **My mind. My house. My state.**

This document defines the sovereign-domain continuity invariant family inside the PEACE Protocol. `PACL` / `Personal AI Compute Layer` is deprecated terminology and MUST NOT be introduced into new normative material.

## Purpose

Digital sovereignty is not the absence of external dependencies. It is the ability to replace operational dependencies without losing constitutional control over the principal's operative domain.

A provider may disappear, compute may degrade, a device may be lost and a hardware backend may change. The system remains sovereign only if the principal can reconstruct identity, authoritative state, rights, relationships, governance and evidence without any lost provider being constitutionally required.

```text
operational dependency != constitutional control
capability to compute != authority to act
```

PEACE does not make compute location irrelevant. Location, provider and hardware may affect disclosure, locality, integrity, capability or trust admissibility. They never become the source of authority.

## Minimum reconstructible domain

`SovereignDomainManifest` requires provider-neutral reconstruction artifacts for:

- identity;
- authoritative state;
- rights;
- relationships;
- evidence chain;
- governance.

The append-only evidence chain is not itself authoritative truth. It proves how operative state was reached, including rejected candidates and corrections. Operative state remains the current governed representation.

External providers may retain caches, sessions, embeddings, model state or other local state. Their state role is explicitly `NON_AUTHORITATIVE` and they are forbidden from becoming a reconstruction dependency.

## Recovery

The logical principal is the root of authority; no single physical credential is the person.

`RecoveryPlan` therefore binds recovery to multiple independent anchors and a threshold. Credentials are rotatable. Recovery restores authority continuity, not old sessions. A recovery event may replace credentials and revoke old device or agent delegations without changing the principal that owns authority.

The contract does not prescribe Shamir sharing, threshold signatures, social recovery or a specific hardware token. Those are interchangeable implementations of the recovery policy.

## Provider-loss test

`assess_provider_loss()` deterministically evaluates a declared failure scenario.

A scenario fails if provider loss removes every reconstructible copy of a required sovereign artifact or makes the configured recovery threshold impossible. Loss of model, compute, sensor or other capability classes may instead be reported as degraded capability.

This distinction is intentional:

```text
loss of capability may degrade service
loss of constitutional state denies sovereignty
```

## Disclosure boundary

A governed projection is a consequence-bearing disclosure when it crosses the principal trust domain.

`DisclosureAuthorization` binds exactly:

- principal and tenant;
- destination;
- purpose;
- projection id and digest;
- source state root and event position;
- allowed object references;
- authority basis and current authority-state digest;
- validity interval.

`assess_disclosure()` is deterministic and fail-closed. Destination drift, projection drift, stale state, stale authority, revoked authority, object-scope expansion or expiry produces `DENY`.

A passing disclosure assessment creates no authority, clearance or disclosure by itself. It only establishes that the exact proposed disclosure is admissible under the supplied current state. Once disclosure has occurred it is not assumed reversible; the control objective is purpose-bound, destination-bound, minimized, time-bounded and auditable disclosure.

Consequence semantics may separately remain sealed until JIT semantic disclosure at the reht boundary.

## Legacy identity bridges

`ExternalIdentityBridge` maps a sovereign principal to a legacy external identifier. The external account, OAuth subject, bank identifier or platform username is explicitly not root identity and creates no authority.

This allows sovereign state to interact with legacy systems without making those systems constitutive of the principal.

## Hardware and model portability

Hardware abstraction is treated as a contract between model semantics and execution implementation, not as a claim that hardware is identical.

The canonical portable unit is `PortableModelArtifact`:

```text
portable model = graph + weights + metadata + semantic contract + requirements
```

A hardware node advertises a `HardwareCapabilityProfile` describing supported formats, operators, precisions, memory and trust roots. A backend-specific `BackendDeploymentArtifact` is explicitly specialized, rebuildable and non-authoritative. It can be deleted and rebuilt from the portable source artifact.

The implementation pattern is compatible with portable IR/runtime/backend designs such as ONNX Runtime, StableHLO or ExecuTorch, but none is a Kernel dependency.

## Semantic equivalence

Hardware replaceability is not established merely because a graph compiles.

`SemanticEquivalenceEvidence` binds the portable model, reference backend, candidate backend, test suite and tolerance profile. `assess_model_portability()` denies a backend when semantic equivalence is absent, failed or bound to another model/backend.

A backend can return:

- `PASS`: requirements are met and semantic equivalence is established;
- `DEGRADED`: execution remains semantically established but requires an explicit fallback path;
- `DENY`: format, memory, precision, operator support or semantic equivalence is insufficient.

A CPU or other reference backend acts as a correctness anchor. Accelerated delegates optimize execution but do not redefine model semantics.

## Portable inference is not portable personal intelligence

Model portability covers execution artifacts. It does not make personal state portable by itself.

The PEACE environment remains separately governed:

```text
identity + authoritative state + rights + relationships + governance + evidence
```

Workers may receive governed projections of that domain. Models, devices, runtimes and compute providers remain replaceable capability suppliers.

## Boundary with execution governance

Sovereign continuity does not authorize external effects.

The canonical PEACE consequence path is:

```text
Person / Principal
  -> Kernel authoritative state
  -> governed projection
  -> disclosure authorization
  -> admissible route
  -> worker / model
  -> candidate commitment
  -> conformance / standing
  -> sealed consequence action
  -> JIT semantic disclosure at reht
  -> fresh commit-time authorization
  -> RACS / external PEP
  -> effect
  -> receipt / evidence
  -> admission
  -> new authoritative state
```

The sovereignty contracts create no direct effect path and no new authority source.

## Formal verification status

The bounded PEACE V0 model in `formal/PersonalDomain.tla` is executed by TLC in GitHub CI. The model explores disclosure, candidate creation, fresh reht authorization, revocation timing, effect gating, provider non-authority and simple recovery continuity. Passing the bounded model is evidence for those modeled invariants only; it is not a proof of every future PEACE implementation or deployment.
