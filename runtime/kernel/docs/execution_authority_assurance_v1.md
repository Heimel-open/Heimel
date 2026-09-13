# Execution Authority Assurance v1

This layer closes the production gap between enterprise authority and a regulated execution/settlement node without moving authority ownership into VALO.

Canonical path:

```text
enterprise authoritative sources
  -> Authority / Delegation / Purpose
  -> fresh AuthorityStateReference
  -> AuthorityLeaseBasis
  -> signed, bounded ExecutionAuthorityLease
  -> signed revocation epoch state
  -> signed execution-node acknowledgement
  -> local revocation checkpoint
  -> per-action lease conformance
  -> fresh REHT authorization
  -> RACS disposition
  -> bank regulated-node acceptance
  -> settlement
  -> execution assurance chain / Veritas
```

## 1. Bounded execution leases

`ExecutionAuthorityLease` is a short-lived, signed capability envelope for a narrowly bounded class of actions. It carries:

- immutable authority-basis digest
- authority and executor identity
- capability and explicit target set
- purpose
- explicit execution-point audience
- digest of the underlying authority constraints and delegation chain
- authority-state dependency digest
- optional single-action and cumulative amount limits
- optional action-count limit
- validity window
- revocation scope, epoch and exact signed revocation-state digest
- issuance nonce
- issuer/key identity and Ed25519 signature

A lease does **not** authorize an external effect. It cannot issue clearance and it cannot bypass REHT/RACS. Its purpose is to avoid remote authority reconstruction for every small transaction while keeping a deterministic local check at every consequence-bearing action.

Lease issuance is fail-closed. Explicit lease targets must be a subset of the effective principal/delegation/purpose scope and lease expiry cannot outlive any bound authority dependency or signed revocation-state validity.

## 2. Revocation is push + signed epoch + acknowledgement + bounded freshness

Push invalidation alone is not considered sufficient. Distributed nodes can miss or reorder messages or become partitioned.

The v1 revocation model therefore combines:

1. a monotonic revocation epoch
2. a signed authoritative `RevocationEpochState`
3. a signed `RevocationNotice` for every epoch transition above zero
4. a node-signed acknowledgement of the exact epoch-state digest
5. a bounded synchronization age
6. short lease validity
7. exact state-digest and epoch equality at local execution evaluation

For epoch zero, the authority source signs the bootstrap state directly. For later epochs, the state can only be issued from a verified notice that produces that exact epoch.

The execution node acknowledges the signed epoch state, not merely transport delivery of a notice. The local checkpoint verifies both source and node signatures and requires the acknowledgement to bind the exact `source_state_digest`.

If the local node cannot establish a current source state and current acknowledgement, the result is `STALE` or `UNKNOWN`; there is no valid execution window.

An old lease remains cryptographically authentic after a revocation, but it becomes operationally ineligible because its embedded epoch and signed revocation-state digest no longer match the current checkpoint. This is intentional:

> valid signature does not imply current authority.

## 3. Every action still requires fresh REHT

`ExecutionLeaseEvaluation` answers only whether the proposed action is inside the still-current cached authority envelope.

It checks:

- lease integrity and issuer signature
- lease/basis binding
- revocation scope, epoch and exact signed state digest
- checkpoint time validity
- execution-point audience
- active lease time window
- capability, target and purpose
- single and cumulative amount limits
- action-count limits
- per-action nonce replay

An `ELIGIBLE` result carries `requires_fresh_reht = true`.

The next boundary remains:

```text
lease conformance -> REHT -> RACS -> external PEP
```

The lease is therefore a latency optimization and attenuation envelope, not an authorization substitute. Generic enterprise constraints that are not represented as lease-local counters or bounds remain authoritative inputs to the fresh REHT decision.

## 4. The bank remains a separate regulated decision node

`BankExecutionAcceptance` is deliberately separate from enterprise authority and REHT.

It binds:

- customer/account binding
- exact action and execution reference
- authority lease and lease-evaluation digests
- revocation checkpoint
- REHT decision reference/digest/disposition
- RACS decision reference/digest/disposition
- bank policy version
- bank AML state digest
- bank sanctions state digest
- bank decision time and validity
- bank signer/key identity and signature

An `ACCEPTED` bank decision is only constructible when the lease evaluation is eligible, REHT is `ALLOW`, and RACS is `ALLOW` or `MODIFY`.

The bank acceptance cannot create enterprise authority and is not itself settlement. In a production adapter, the referenced REHT/RACS artifacts must be independently verified before their digests are admitted to this contract.

## 5. Settlement closes the regulated effect boundary

`SettlementEvidence` binds the exact accepted action/execution to:

- bank acceptance digest
- rail
- effect reference
- settlement status
- commit time
- external receipt digest
- settlement signer/key and signature

A `COMMITTED` settlement requires a previously `ACCEPTED` bank decision and must occur inside that acceptance window.

`ExecutionAssuranceChain` then content-addresses the complete chain:

```text
authority basis
  -> lease
  -> revocation checkpoint
  -> action lease evaluation
  -> bank acceptance
  -> settlement
  -> optional outcome evidence
```

This is suitable as a Veritas/evidence envelope. It does not claim that cryptography proves legal validity or the truth of an external source; it proves artifact integrity, signer authenticity and exact binding between the recorded steps.

## 6. Fail-closed invariants

The implementation rejects or marks ineligible when any of the following occur:

- stale or tampered authority basis
- lease scope widening
- invalid lease signature
- expired lease
- invalid revocation-source signature
- invalid execution-node acknowledgement signature
- acknowledgement of a different revocation-state digest
- missing or stale revocation acknowledgement
- node/source epoch divergence
- old lease after a new revocation epoch
- stale revocation checkpoint at action time
- endpoint outside lease audience
- action outside capability/target/purpose
- replayed action nonce
- amount or action-count budget exhaustion
- bank acceptance without REHT ALLOW
- bank acceptance without compatible RACS disposition
- settlement outside the bank acceptance window
- action or execution drift between acceptance and settlement
- digest tampering anywhere in the assurance chain

## 7. Production deployment

The included Ed25519 signer is a reference adapter. Production deployments should inject an HSM/KMS-backed signer with equivalent domain-separated signing semantics.

Revocation distribution transport is intentionally provider-neutral. Kafka, NATS, cloud event buses, bank-native messaging or dedicated control channels may carry notices, signed epoch states and acknowledgements, but transport success is not itself trusted as authority. The execution node must still prove a current signed revocation checkpoint before treating a lease as eligible.
