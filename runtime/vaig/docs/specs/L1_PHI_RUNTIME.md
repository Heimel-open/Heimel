# L1 Phi Runtime Layer

Status: draft v1.0
Scope: deterministic execution-boundary runtime
Boundary: L1 does not reason and does not construct policy

## Purpose

L1 determines whether a proposed transition may occur.

It preserves execution integrity by enforcing the admissible state boundary.

## Pipeline

```text
Candidate
-> State Projection
-> Integrity Functional
-> Dynamic Lambda
-> Phi Decision
-> Receipt
-> Commit
```

## Input

- current state
- candidate transition
- environment e from VAIG
- previous receipt hash

## Output

- ALLOW
- BLOCK
- DEFER
- HALT
- receipt
- committed or preserved state

## State projection

Raw output is mapped into operational state:

```text
P: O -> X
```

Projection must be deterministic, reproducible, idempotent and replayable.

## Integrity functional

L1 computes:

```text
F_free(x, e)
```

using geometry, transition energy, barrier potential and deterministic constraints.

## Dynamic lambda

L1 computes:

```text
lambda(e)
```

from trust, authority, isolation, domain, criticality and mode.

## Decision rule

```text
ALLOW iff F_free(x_next, e_next) <= lambda(e_next)
```

## Commit rule

Only ALLOW may update state.

BLOCK, DEFER and HALT preserve the previous valid state.

## Receipt rule

Every decision must write a receipt.

## Contract

```text
L1 authorizes or blocks transition.
L1 does not reason.
L1 does not define governance context.
```
