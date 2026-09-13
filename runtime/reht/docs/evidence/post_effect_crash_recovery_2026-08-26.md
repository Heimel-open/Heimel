# Post-effect crash recovery — 2026-08-26

Base: `02abc7c24a85185e81c29ebb340c8d87bbb303cd`

This change closes the consequence-window where a process could die after a real-world effect had started but before terminal evidence was durably closed.

## State machine

`INTENT_OPEN -> EFFECT_INVOKING -> RECEIPT_READY -> EVIDENCE_CLOSING -> CLOSED`

The journal is subordinate mechanical evidence. It cannot grant authority and it never retries an external effect.

## Recovery semantics

- `INTENT_OPEN` + unused permit: `NOT_STARTED`.
- `INTENT_OPEN` + consumed permit: `INDETERMINATE_EFFECT`.
- `EFFECT_INVOKING`: `INDETERMINATE_EFFECT`; no automatic replay.
- `RECEIPT_READY`: only evidence closure may resume; the effect cannot be rerun.
- `EVIDENCE_CLOSING`: `INDETERMINATE_EVIDENCE_CLOSURE`; no automatic evidence replay because Veritas/Kernel may already have committed.
- `CLOSED`: terminal and non-replayable.

`RECEIPT_READY` is admitted only when the receipt re-binds the exact permit, action digest, execution-context hash, clearance, effect name and REHT `ALLOW`, and its receipt digest recomputes exactly. Evidence closure must bind the same receipt and must not grant authority.

A consumed permit with no prior terminal journal record cannot be rewritten as a clean `PERMIT_REPLAY/BLOCKED` outcome. It remains explicitly indeterminate for reconciliation.

## Falsification

CPU-only crash probing was run with seed `20260826` against branch logic at `d1c676c3af319155601d382263e731753fec522f` before the final receipt-integrity hardening:

- 100 hard exits inside the effect: 100 classified `INDETERMINATE_EFFECT`, 0 effect replays.
- 100 hard exits after `RECEIPT_READY`: 100 evidence-only reconciliations, 0 effect replays.
- 100 hard exits at `EVIDENCE_CLOSING`: 100 remained explicitly indeterminate, 0 automatic reconciliation.
- 1,000 duplicate intent attempts: 0 reopened executions.

Machine-readable evidence: `validation/results/post_effect_crash_recovery_20260826_local.json`.

## Provenance limitation

A native Git checkout could not be obtained in the available local runtime because `github.com` DNS resolution failed. GitHub Actions also remains unusable when jobs fail before startup. Therefore no native-checkout full-suite PASS is claimed for the final head; the evidence file records this limitation explicitly.

## Claims not made

- No distributed multi-host consensus guarantee.
- No exactly-once guarantee for arbitrary external systems.
- No automatic resolution of indeterminate real-world outcomes.
- No new authority owner: Kernel remains operative-state owner and REHT remains the sole execution-authorization owner.
