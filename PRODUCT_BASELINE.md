# Product Baseline — valo-insurance-pack v0.1.0

**Status: FROZEN.** No new features before the market test. Only bug fixes and
carrier-pilot-facing material are permitted on top of this baseline.

## Frozen product slice

```text
AssuranceProfileV1
  -> CommitAssuranceEvaluationV1  (capability-set subsumption, fail-closed)
  -> reht                          (sole authorization boundary)
  -> RACS                          (signed GovernanceClearance verification)
  -> Gateway/PEP                   (execution enforcement point)
  -> Veritas                       (write-once receipt attestation)
  -> ClaimsEvidencePackV1          (deterministic, offline-verifiable)
```

## What the baseline proves

1. Missing observability is `UNKNOWN`, never presumed ACTIVE/UNCHANGED.
2. Supplied `evidence_digest` must exactly match the computed digest.
3. No synthetic REHT clearance and no direct tool invocation: consequence is
   reachable only through a real Gateway/PEP.
4. Assurance strength is capability-set subsumption
   (`required_capabilities ⊆ actual_capabilities`), not a linear ranking.
5. The real-chain test runs reht → signed RACS clearance → Gateway → Veritas
   and binds the verified RACS digest into the claims pack.

## Acceptance gate

- CI green on head (`ruff check .`, `pytest tests/`).
- `v0.1.0` tag points at the merged product commit.

## Out of scope until market test completes

- New carriers/coverage conditions (sample profiles only).
- New source mechanisms beyond the capability table in
  `contracts/assurance_strength.py`.
- Any change to the frozen chain order above.
