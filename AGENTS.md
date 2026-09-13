# valo-insurance-pilot

## What this is

Carrier-facing pilot material built on the **frozen** `valo-insurance-pack`
v0.1.0 baseline. It must never extend the core product slice.

## Non-negotiables

1. **Non-authority of insurance**: the pilot material must always present the
   insurance layer as evaluating/attesting, never authorizing execution.
2. **Freeze**: no new core features, no new carriers/coverage conditions beyond
   the sample, no new source mechanisms.
3. **Accuracy**: generated sample artifacts must verify offline
   (`verify_claims_evidence_pack`) before being committed.
4. **No synthetic claims pack presented as real**: sample packs are labeled
   synthetic; real artifacts come from the shadow pilot.

## Layout

```
scenario/            # high-value procurement narrative + draft policy condition
sample-profile/      # sample AssuranceProfileV1 (JSON)
sample-claims-pack/  # sample ClaimsEvidencePackV1 (JSON, offline-verifiable)
architecture/        # one-page architecture
scripts/             # sample generator (reproducible)
```

## Reproduce samples

```bash
PYTHONPATH=/path/to/valo-insurance-pack/src python3 scripts/generate_sample_claims_pack.py
```

## Conventions

- No secrets in the repo.
- Generated JSON artifacts are committed (deterministic samples) so carriers
  can verify offline without a build.
