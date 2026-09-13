# Canonical execution architecture

## Authority and boundary

AiPlsCore is the repository's only canonical enforcement core.
GoldenExecutionPath is the sole supported commit path to ExclusiveEffector.
RacsBridge verifies a signed RACS artifact, checks issuer/key/tenant/trust
domain/time and revocation, validates its action-envelope digest, and translates
it into the core inputs.

```text
VAIG evaluation → REHT clearance receipt → signed RACS permit
→ RacsBridge verification → durable permit consumption
→ AiPlsCore ALLOW → ExclusiveEffector → execution receipt
```

`ExclusiveEffector::execute` requires an unforgeable
`ExecutionAuthorization`; only GoldenExecutionPath constructs it. Every known
call site is:

1. `ai-pls-golden-path/src/lib.rs`, inside `GoldenExecutionPath::process`.

Other occurrences are trait implementations, not calls.

## Commit ordering

1. Verify permit signature, issuer, role, key activity, tenant, trust domain,
   validity, and payload digest.
2. Verify action, connector, clearance, target, payload, nonce and permit
   binding; check revocation.
3. Atomically reserve and append consumption; `sync_all` before continuing.
4. Perform the final AiPlsCore state check.
5. Call the effector only after ALLOW.
6. Produce an execution receipt, including attempted failures.

Consumption is append-only and hash-linked. Startup rejects malformed,
inconsistent, duplicate, or broken-chain records. Nonces remain consumed after
effector failure and process restart. Any registry failure is fail-closed.

## Evidence types

Clearance receipts, permit/commit evidence, and execution receipts are distinct.
Shadow receipts and legacy audit entries must not be labeled execution receipts.

## Legacy adapter

`l1-guardian`, ValoGuardrail, CRC/F1/F2a frame processing, and the Python
telemetry pipeline are compatibility adapters. The 64-byte frame is one legacy
transport format, not the canonical runtime contract. Legacy functionality is
retained, and malformed telemetry now aligns internal HALT state, external HALT
response, and audit.

## Formal and operational limits

The separate AiPlsCore TLA+ model checks a bounded abstract state machine. It
does not formally verify the Rust runtime, Ed25519 permit verifier, durable
filesystem behavior, or effector. No refinement mapping exists yet.
Hardware-backed human reset and production WORM storage are not connected.
The Python WORM log is a file-based simulation.
