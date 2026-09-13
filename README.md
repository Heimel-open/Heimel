# VALO V5 Core

Historically this repository was described as “REHT V5 Core”; that name now
refers to the wider authorization context, not the enforcement implementation.

This repository implements one canonical consequence-bearing execution chain:

```text
VAIG evaluates
→ REHT clears
→ RACS standardizes and signs a permit
→ RacsBridge verifies and translates it
→ AiPlsCore enforces
→ GoldenExecutionPath commits
→ ExclusiveEffector executes
→ execution receipt
```

`AiPlsCore` is the only canonical enforcement core.
`GoldenExecutionPath` is the only supported commit boundary to a
consequence-bearing effector. Before an effector can be called, the path checks
the permit and exact binding, revocation, issuer and validity through the RACS
bridge; durably reserves consumption with `sync_all`; and obtains an ALLOW from
AiPlsCore. Registry failure, corruption, replay, or binding failure denies or
halts without a side effect.

The L1 `ValoGuardrail`, 64-byte frame protocol, and Python telemetry path remain
compatibility adapters. They do not own independent governance semantics and
are not the canonical execution boundary.

## Protected Boundary

Legacy compatibility is preserved: Do not change l1-guardian/src/validation_logic.rs
without separately updating its model and
test vectors. This canonical-boundary change only corrects telemetry state
consistency in `l1-guardian/src/server.rs`.

## Evidence separation

- Clearance receipt: REHT's decision (external input).
- Permit/commit evidence: verified RACS permit plus durable consumption record.
- Execution receipt: actual allowed/attempted/applied effector result.

An audit entry or a shadow receipt is not an execution receipt.

## Modes

- `shadow`: verifies and reports `would_execute`; never calls an effector or
  reserves a production nonce.
- `integration`: may call a verified synthetic effector through the canonical
  path.
- `legacy telemetry`: compatibility testing for existing frame consumers.

Run the Rust demo modes:

```sh
cargo run --manifest-path ai-pls-racs-bridge/Cargo.toml --bin shadow_demo -- shadow
cargo run --manifest-path ai-pls-racs-bridge/Cargo.toml --bin shadow_demo -- integration
```

## Verification scope

TLA+ models bounded state machines. `formal-verification/AiPlsCore.tla` is a
separate model for the new core. Formal verification does not currently cover
the complete Rust, permit, filesystem, or effector chain because no
code-to-spec refinement mapping exists. Human reset is capability-restricted,
but hardware-backed/YubiKey authorization is not connected. The Python WORM
implementation is a file-backed simulation, not production WORM storage.
