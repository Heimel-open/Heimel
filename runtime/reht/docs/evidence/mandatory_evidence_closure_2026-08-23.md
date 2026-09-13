# Mandatory evidence closure — two-core runtime

Date: 2026-08-23
Base: `9ac79b99973f8f481a83ee39e60478ce3287501f`
Branch: `fix/mandatory-evidence-closure`

## Objective

Close the final semantic-audit gap without introducing a third authoritative core.

Canonical authority/state ownership remains:

- **Kernel** — operative state and canonical append-only history.
- **REHT** — sole execution-authorization boundary.
- **Veritas** — non-authoritative evidence verification/WORM admission only.

## Required production path

```text
Kernel fresh execution context
  -> REHT exact-action authorization
  -> EffectBoundary consequence
  -> exact terminal ExecutionReceipt
  -> Veritas receipt verification + WORM append
  -> Veritas-backed verified execution outcome
  -> Kernel EXTERNAL_EFFECT_OBSERVED append
  -> evidence closure
```

An EffectBoundary terminal result is not production evidence-closed until both downstream references exist.

## Enforced invariants

1. Production `EffectBoundary` requires an explicit `ExecutionEvidenceClosureSink`.
2. `DevelopmentEvidenceClosureSink` is rejected by production construction; test/dev must opt in with `EffectBoundary.for_development()`.
3. The production `VeritasKernelExecutionEvidenceSink` always calls Veritas before Kernel.
4. Veritas receives the exact `valo.reht.effect-boundary-observation.v1` receipt payload and verifies the receipt digest before WORM admission.
5. Kernel receives an outcome only after a Veritas WORM reference exists.
6. Kernel admission is `EXTERNAL_EFFECT_OBSERVED`; the existing Kernel reducer is no-op for operative state, so evidence cannot recreate or extend authority.
7. `authority_granted` is hard false through receipt, closure and Kernel outcome.
8. Veritas failure stops before Kernel admission.
9. Kernel failure after WORM is surfaced as `EvidenceClosureError(stage="KERNEL")` with the Veritas reference preserved; it is never reported as closed.
10. Receipt-id mismatch or a sink claiming closure without both Veritas and Kernel references fails closed.

## Dependency anchors

- `nsolland/valo-kernel` — `c1d8daad1bf85019f771c7388c7953bb7a37859c`
  - provides `VerifiedExecutionOutcomeV1` and `KernelExecutionOutcomeConsumer`.
- `nsolland/Veritas` — `7657c6463356b6e7902b620fedbca27ec96294f9`
  - provides strict EffectBoundary receipt verification and existing WORM admission.

The Python package uses structural ports rather than importing these repositories directly. This preserves the two-core authority model: Veritas participates in evidence closure, not authorization.

## Falsification coverage

`tests/test_mandatory_evidence_closure.py` covers:

- production rejection of the development sink;
- explicit dev mode never claiming durable closure;
- Veritas-before-Kernel ordering;
- Veritas failure preventing Kernel admission;
- Kernel failure after WORM producing explicit incomplete closure;
- production ALLOW returning only after closed evidence;
- restrictive REHT outcomes also being evidence-closed before return.

Existing EffectBoundary/interlock tests are migrated to explicit development mode where durable external evidence is not under test. Production RealReht/Kernel integration tests use a closed evidence sink and assert `evidence_closure.closed is True`.

## Result

The previously open audit item — **mandatory `EffectBoundary -> Veritas WORM -> Kernel outcome` wiring** — is implemented. No new decision vocabulary, policy engine, authority owner, or direct-effect path is introduced.
