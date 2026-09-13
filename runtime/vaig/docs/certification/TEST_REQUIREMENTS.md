# Phi Runtime Test Requirements

Status: draft v1.0
Scope: required tests for Phi Runtime conformance

This document defines the minimum test families required for a Phi Runtime implementation.

## 1. Unit tests

Required coverage:

- state projection
- free-energy functional
- dynamic lambda
- Phi decision
- receipt generation
- commit rule

## 2. Decision tests

Required scenarios:

- small valid transition -> ALLOW
- low-trust context -> BLOCK
- boundary crossing -> BLOCK
- authority violation -> BLOCK
- missing evidence -> BLOCK or DEFER
- invalid environment -> HALT or DEFER
- invalid receipt chain -> HALT
- critical mode -> near-zero permeability
- halt mode -> HALT

## 3. Invariant tests

Required invariant:

```text
No non-ALLOW decision commits candidate state.
```

Required invariant:

```text
Every ALLOW decision must satisfy F_free(x_next, e_next) <= lambda(e_next).
```

Required invariant:

```text
Every decision writes a receipt.
```

## 4. Replay tests

A recorded trace must replay exactly.

Replay must verify:

- same projected states
- same free-energy values
- same lambda values
- same decisions
- same receipt hashes
- same committed state sequence

## 5. Fuzz tests

Fuzz tests must generate random:

- states
- candidates
- environments
- authority levels
- trust levels
- criticality levels
- receipt-chain states

Required property:

```text
Invalid, unknown or malformed input must never produce ALLOW by default.
```

## 6. Monte Carlo stress tests

Monte Carlo tests must generate large numbers of random transitions.

Required property:

```text
No ALLOW decision may violate the admissibility condition.
```

Minimum draft target:

```text
100000 random transitions
0 invariant violations
```

## 7. Formal model tests

A formal model should verify:

- ALLOW commits only admissible transitions
- BLOCK preserves previous state
- DEFER preserves previous state
- HALT preserves previous state
- every decision writes a receipt
- broken receipt chain causes HALT

TLA+ is recommended but not mandatory for draft implementations.

## 8. Benchmark tests

Benchmark separately from model inference.

Required measurements:

- state projection latency
- free-energy evaluation latency
- lambda calculation latency
- Phi decision latency
- receipt generation latency
- replay verification throughput

## 9. Reference vector suite

Each implementation must include fixed vectors for:

- normal allow
- normal block
- critical allow
- critical block
- halt
- authority violation
- receipt-chain continuation
- receipt-chain break

## 10. Current repo seed

The current seed test is:

```text
tests/test_free_energy_governance.py
```

It is a toy invariant test and not a full conformance suite.
