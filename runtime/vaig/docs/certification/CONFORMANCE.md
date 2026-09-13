# Phi Runtime Conformance

Status: draft v1.0
Scope: conformance requirements for Phi Runtime implementations

A system may claim Phi Runtime conformance only if it passes the requirements in this document.

## 1. Conformance levels

### Level 1 - Deterministic Core

Required:

- deterministic state projection
- deterministic free-energy calculation
- deterministic lambda calculation
- deterministic Phi decision
- commit rule enforcement
- receipt generation

### Level 2 - Replayable Runtime

Requires Level 1 plus:

- replay from recorded inputs
- hash-chain receipt verification
- fixture-based reference vectors
- BLOCK/DEFER/HALT state preservation tests

### Level 3 - Verified Runtime

Requires Level 2 plus:

- invariant test suite
- fuzz test suite
- Monte Carlo stress suite
- formal model or TLA+ invariant proof
- benchmark results

## 2. Required decision semantics

Implementations must support:

- ALLOW
- BLOCK
- DEFER
- HALT

Semantics:

- ALLOW commits candidate state
- BLOCK preserves previous state
- DEFER preserves previous state and routes to higher authority or RRP
- HALT preserves previous state and stops governed execution path

## 3. Determinism requirement

Given identical inputs, implementation must produce identical:

- projected state
- free-energy value
- lambda value
- decision
- receipt hash

## 4. Receipt requirement

Every decision must emit a receipt.

Minimum receipt fields:

- sequence number
- runtime id
- state hash
- candidate hash
- environment hash
- authority hash
- policy hash
- decision
- previous receipt hash
- receipt hash

## 5. Replay requirement

A verifier must be able to replay an execution trace and confirm:

- every decision is reproduced
- receipt hashes match
- committed states match
- rejected states were not committed

## 6. Invariant requirement

A conformant implementation must show:

```text
If x_0 in K(e_0) and only ALLOW commits, then committed x_t remains in K(e_t).
```

## 7. Failure behavior

Unknown or invalid runtime state must not default to ALLOW.

Required fallback:

- invalid projection -> HALT or DEFER
- invalid environment -> HALT or DEFER
- invalid receipt chain -> HALT
- missing authority -> BLOCK or DEFER
- missing evidence in evidence-bound contexts -> BLOCK or DEFER

## 8. Performance reporting

Implementations must report:

- p50 decision latency
- p95 decision latency
- p99 decision latency
- receipt generation latency
- replay throughput

Performance claims must be measured independently from LLM inference latency.

## 9. Claim boundary

Conformance does not mean legal compliance, regulatory approval, insurance acceptance or universal AI safety.

Conformance means the implementation follows the Phi Runtime execution-boundary contract.
