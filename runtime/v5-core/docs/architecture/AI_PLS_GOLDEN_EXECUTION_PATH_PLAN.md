# AI-PLS Golden Execution Path Plan

## Scope

This plan covers the missing end-to-end production chain around the existing
`ai-pls-core` enforcement kernel.

It does not change:

- `ai-pls-core`
- `l1-guardian`
- the legacy safety semantics already frozen in the old core

It focuses on the narrow execution path that still needs to be proven as one
atomic, deterministic chain.

## What is already established

- `ai-pls-core` is a dependency-free enforcement core.
- `HumanResetAuthorization` is not externally constructible in normal use.
- `adapters/legacy-telemetry` is the compatibility bridge for old telemetry.
- `docs/AI_PLS_MIGRATION.md` already describes shadow migration.
- `l1-guardian` remains the historical safety boundary.

## What is now proven end to end

The repo now shows one complete golden path from permit to physical effect:

```text
Action Envelope
  -> REHT clearance
  -> cryptographic binding
  -> AI-PLS enforcement
  -> exclusive effector
  -> actual side effect
  -> execution receipt
```

The main remaining property is not the existence of each object. The proven
path must continue to guarantee:

1. a deny produces zero effect,
2. only one effector path can execute,
3. a permit is cryptographically bound to the exact envelope it authorizes,
4. the receipt corresponds to the effect that actually occurred.

## Recommended implementation order

### 1. Define the golden path boundary

Create one explicit adapter or runtime boundary that is the only approved path
from clearance into execution.

That boundary should:

- accept the signed clearance envelope
- bind the clearance to the action envelope digest
- pass one normalized execution signal into `ai-pls-core`
- dispatch to one exclusive effector adapter only after allow
- emit one canonical receipt

### 2. Quarantine all direct effectors

Any direct API, database, connector, or tool path that can cause side effects
without the golden path should be classified as legacy or quarantined.

The rule is simple:

- if it can execute without the golden path, it is not yet part of the
  enforced production chain

### 3. Add end-to-end tests for deny and allow

The first tests should prove the enforcement boundary, not AI quality.

Minimum cases:

- deny means no side effect
- invalid binding means deny
- expired clearance means deny
- replay means deny
- sticky halt blocks later execution
- human reset only resumes through the authorized path
- allow produces one receipt and one effect only

### 4. Add receipt correlation

The receipt must carry enough identity to prove the exact path that executed:

- action envelope digest
- clearance digest or clearance id
- effector id
- outcome state
- replay nonce or equivalent anti-replay reference
- timestamp or ordering token

### 5. Keep the shadow path narrow

The current shadow demo should stay constrained to one low-risk permit path.
That gives a narrow proof before any broader migration.

### 6. Retire legacy direct execution only after parity

Legacy paths should remain available only until:

- the golden path is proven locally
- parity is demonstrated against the legacy path and shadow demo
- receipts match the expected behavior
- deny remains zero-effect under all tested failure modes

## Acceptance criteria

The golden path is ready only when all of the following hold:

- `ai-pls-core` remains unchanged and enforcement-only
- no production path bypasses the golden boundary
- a deny cannot produce any observable side effect
- a permit produces exactly one effect and one receipt
- replay, expiry, and invalid binding are rejected
- cancellation or halt invalidates later execution
- tests prove the behavior locally

## What not to do

- Do not add policy interpretation to `ai-pls-core`.
- Do not let the legacy telemetry adapter become a second execution route.
- Do not treat AI confidence as a runtime authority input in the new path.
- Do not merge more legacy semantics into the new core.
- Do not widen the boundary before the zero-effect guarantee is proven.

## Working hypothesis

The correct next move is not another concept.

It is a single, narrow, testable execution path that can prove:

```text
deny -> no effect
allow -> one effect
receipt -> exact correlation
```

Once that is true, the rest of the platform can be migrated around it
without changing the enforcement core.
