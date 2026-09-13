# Production effect-boundary fix — 2026-08-23

Repository: `nsolland/valo-reht`
Base: merged PR #37, merge SHA `75f8b9d57f82355204b9a965123a842b345ac2f2`
Branch: `fix/production-effect-boundary`

## Problem

PR #37 proved the two-core semantics through a TEST-ONLY mechanical effect adapter. That left one implementation caveat: the authoritative design had no production effect-boundary implementation inside `valo-reht`.

## Fix

Added `src/valo_reht/effect_boundary.py` as the production mechanical commit path subordinate to REHT.

Properties:

- takes the proposed action and freezes an exact snapshot before authorization;
- obtains the execution context inside the commit call through a context factory;
- calls REHT itself, so there is no separate post-authorization action-substitution channel;
- invokes no effect for `DENY` or `STEP_UP`;
- requires `ALLOW` + permit + execution-context binding;
- verifies the execution-context hash before commit;
- consumes the permit before effect invocation;
- requires an atomic `PermitStore` for single-use enforcement;
- production `PermitStore` implementations must provide shared/durable semantics suitable for restart and multi-worker execution;
- `InMemoryPermitStore` is explicitly test/single-process-development only;
- failed external invocation does not re-arm the permit;
- the effect receives the exact action snapshot that REHT authorized;
- the boundary creates no authority and performs no policy inference.

`EffectBoundary`, `EffectCommitResult`, `EffectDenied`, `PermitStore`, and `InMemoryPermitStore` are exported by `valo_reht`.

## Validation

Dedicated production-boundary tests cover:

- DENY -> no effect;
- STEP_UP -> no effect;
- exact authorized action snapshot reaches the effect;
- ALLOW without permit fails closed;
- execution-context binding mismatch fails closed;
- permit replay denied;
- 12-way concurrent replay -> exactly one commit;
- failed effect invocation leaves the permit consumed.

The same production `EffectBoundary` is also integrated against `RealReht` + Kernel test fixtures for:

- valid ALLOW commit;
- revocation observed before commit -> DENY;
- STEP_UP -> no effect.

Isolated validation of the production boundary implementation: `8 passed` before the permit-store hardening. The hardened implementation preserves the same boundary semantics while moving replay state behind the required atomic store contract.

Full repository validation remains subject to the repository environment because GitHub Actions is currently failing at workflow startup and this assistant runtime cannot clone GitHub over DNS.

## Result

The effect boundary is no longer TEST-ONLY. The test-only two-core harness may remain as a regression fixture, but the mechanical governed effect path now has a production implementation in `src/valo_reht`.

The production boundary itself does not assume process-local replay state. Deployment must provide a shared/durable atomic `PermitStore`; this is a concrete runtime dependency of the effect boundary, not a new authority core.

AUTHORITATIVE RUNTIME = KERNEL + REHT
