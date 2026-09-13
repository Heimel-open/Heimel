# AI-PLS migration

The existing `l1-guardian` remains unchanged.

The new `ai-pls-core` is a parallel, dependency-free enforcement kernel. Migration is adapter-led and reversible.

For the next implementation step, see:

- [`docs/architecture/AI_PLS_GOLDEN_EXECUTION_PATH_PLAN.md`](./architecture/AI_PLS_GOLDEN_EXECUTION_PATH_PLAN.md)

## Target chain

```text
VAIG evaluates
REHT clears
RACS transports a signed clearance envelope
AI-PLS Core enforces
Execution proceeds or stops
```

## Migration phases

1. Validate the new core independently.
2. Add a RACS clearance-envelope adapter.
3. Mirror legacy clearance inputs into AI-PLS in shadow mode.
4. Compare state transitions and receipts.
5. Move one non-critical execution path to AI-PLS.
6. Retire the legacy clearance adapter only after parity is proven.

The local demo harness now exposes that migration shape explicitly:

- `python simulate.py` runs the legacy telemetry demo
- `python simulate.py --mode shadow` runs the legacy telemetry demo plus the
  permit-path shadow demo
- `python simulate.py --mode parity` emits an explicit legacy-vs-shadow
  alignment report
- `python simulate.py --mode parity --report-json=path` writes the same
  alignment report as a JSON artifact
- `python scripts/parity_report.py --input path/to/report.json` summarizes the
  artifact and exits non-zero when the paths are not aligned
- `python scripts/verify_worm_log.py --input path/to/valo_audit_YYYYMMDD.log`
  verifies a chained WORM audit log artifact and exits non-zero on tampering

## Hard boundary

AI-PLS Core must never import model, semantic, policy or governance evaluation code.
