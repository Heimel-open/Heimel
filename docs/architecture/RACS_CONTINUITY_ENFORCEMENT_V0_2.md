# RACS Continuity Enforcement — Core Profile 0.2

Status: implemented Core ingress profile  
Contract owner: RACS  
Enforcement owner: REHT V5 Core

## Purpose

This profile defines how the bounded Core accepts and enforces a signed RACS runtime-continuity result after a governed execution session has already been admitted and permitted.

The Core does not repeat RACS verification semantics. It verifies the authenticity, integrity and exact execution bindings of a signed accepted result, then maps it to an existing bounded directive.

## Signed ingress artifact

Artifact type: `RACS_CONTINUITY_ENFORCEMENT`

Required envelope properties:

- schema version `0.2.0`
- profile `racs-core-0.2`
- canonicalization `RACS-JCS-1`
- Ed25519 signature from a trusted issuer with role `RACS_CONTINUITY_AUTHORITY`
- exact tenant and trust-domain binding
- current envelope validity window
- byte-exact payload digest

The payload binds:

- governed session
- execution identity
- Core execution permit identity and digest
- commit token identity and digest
- RACS continuity decision identity and digest
- continuity sequence
- current and effective runtime-bound digests
- RACS verification decision and normalized reason code
- optional narrowing-proof digest
- validity and idempotency

## Accepted mappings

| RACS decision | Required verification evidence | Core directive |
|---|---|---|
| `CONTINUE` | `ACCEPT`, unchanged bounds | `Continue` |
| `MODIFY_RUNTIME_BOUNDS` | `BOUNDS_NARROWED`, changed bounds, proof digest | `ApplyNarrowedBounds` |
| `PAUSE` | `ACCEPT`, unchanged bounds | `Pause` |
| `REAUTHORIZE` | `ACCEPT`, unchanged bounds | `Pause` |
| `ROLLBACK` | `ACCEPT`, unchanged bounds | `Pause` |
| `HANDOVER` | `ACCEPT`, unchanged bounds | `Pause` |
| `STOP` | `ACCEPT`, unchanged bounds | `Stop` |
| `HALT` | `ACCEPT`, unchanged bounds | `Halt` |

Unknown combinations fail closed.

## Durable enforcement state

`DurableContinuityRegistry` stores append-only JSONL records with synchronous persistence.

For each execution it enforces:

- no duplicate authorization artifact
- no duplicate idempotency key
- continuity sequence increases by exactly one
- `current_bounds_digest` equals the previously enforced effective bounds
- first continuity action binds the initial permitted bounds
- paused execution cannot resume through continuity
- stopped execution cannot resume through continuity
- halted execution is terminal

A fresh permit and commit-token chain is required to resume after pause or stop. HALT remains subject to the existing human-only reset path.

## Core state boundary

Per-execution STOP and effective-bound state remain in the durable continuity registry.

The global L1 Guardian receives only effects it already owns:

- append and sign an audit event
- escalate Active to Degraded for pause
- invoke the existing emergency HALT transition

`Continue` and bounds modification never reset or improve the global guardrail state. No automated continuity directive can construct the human authorization required for reset.

## Excluded surfaces

This delivery does not change:

- `validation_logic.rs`
- formal verification specifications
- REHT or RACS admissibility semantics
- human-only reset authority
- execution-permit or commit-token issuance

## Failure policy

Signature, digest, tenant, trust-domain, permit, token, session, sequence, bounds or validity mismatch returns a typed error and no directive is applied.

Registry corruption or lock failure is treated as unavailable and fails closed.
