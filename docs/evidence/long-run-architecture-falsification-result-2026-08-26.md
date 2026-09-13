# Long-run architecture falsification — result

Date: 2026-08-26
Canonical repo SHA tested: `a56978bf831ad8c93e613086d4ffd6dcf6704faa`
Seed: `20260826`
Classification: **PASS_WITH_EXECUTION_PROVENANCE_LIMITATION**

## Result

All eight preregistered adversarial families passed at approximately 10x the initial run scale.

| Family | Scale | Result | Safety failures |
|---|---:|---|---:|
| Permit concurrency | 64,000 concurrent attempts / 2,000 races | PASS | 0 duplicate effects |
| Late-HALT TOCTOU | 100,000 | PASS | 0 unsafe commits |
| Exact action snapshot | 100,000 | PASS | 0 snapshot escapes |
| Hierarchical resource ceilings | 800,000 reservation attempts | PASS | 0 parent oversubscriptions |
| Active-session continuity | 100,000 drift/reauth cases | PASS | 0 stale continuations; 100,000 widen attempts rejected |
| Evidence ordering | 100,000 | PASS | 0 false closures |
| Malicious closure mismatch | 50,000 | PASS | 0 accepted mismatches |
| Non-authority/direct bypass | 50,000 iterations | PASS | 0 authority creation; 0 direct bypass |

Observed family CPU time was about 45.6 seconds in aggregate.

## Specific falsification results

### Permit concurrency

- 64,000 commit attempts across 2,000 32-way races.
- Exactly 2,000 commits.
- 62,000 replay attempts rejected.
- External-effect count remained exactly one per permit race.

### TOCTOU / late HALT

100,000 cases injected `HALT_GLOBAL` after the synthetic REHT object had computed ALLOW but before `EffectBoundary` permit consumption.

Observed:

- unsafe commits: 0
- external effects: 0
- permit consumptions after late HALT: 0

### Exact snapshot

100,000 caller-owned action proposals were mutated after boundary entry. The executed effect snapshot remained the original authorized action in every case.

### Hierarchical resource ceiling

800,000 randomized sibling reservation attempts were issued against shared parent budgets.

- 451,406 accepted within the envelope.
- 348,594 rejected at the ceiling.
- parent oversubscriptions: 0.

### Long-running session continuity

100,000 context-drift cases:

- all 100,000 forced REAUTHORIZE;
- all 100,000 denied reauthorizations ended HALTED;
- all 100,000 attempted runtime-bound widenings were rejected;
- stale continuations observed: 0.

### Evidence closure

100,000 Veritas/Kernel ordering cases:

- 33,334 successful closures;
- 33,333 Veritas failures stopped before Kernel;
- 33,333 Kernel failures after Veritas were surfaced as incomplete closure;
- false `closed=True`: 0.

An additional 50,000 mismatched-receipt closure attempts were rejected.

### Non-authority surfaces / direct effect

Across 50,000 repeated iterations:

- probe attempt to grant execution authority: always rejected;
- sensor/session observation attempt to grant authority: always rejected;
- direct `BoundaryEffect.invoke()` bypass: always blocked by `NO_DIRECT_EFFECT_PATH`.

## Execution provenance

The intended GitHub Actions run could not start. Both pull-request and main-push attempts ended as GitHub `startup_failure` before any job executed. This is neither PASS nor FAIL.

A Railway fallback was also attempted. Railway accepted the repository/service configuration but never created a deployment object, so no Railway execution result is claimed.

The completed run therefore used the OpenAI local CPU container. The five production modules exercised by the harness were fetched from GitHub at the canonical repo SHA through the GitHub connector and formatting-normalized into a minimal local Python package without intended semantic changes. Their GitHub blob SHAs are recorded in the machine-readable evidence file.

This is stronger than a synthetic reimplementation, because the tested logic was extracted from the canonical source, but it is **not** author-independent/native-checkout replay. Therefore the result is deliberately classified `PASS_WITH_EXECUTION_PROVENANCE_LIMITATION`, not `VERIFIED`.

## Remaining falsifier

When a valid checkout-capable runner becomes available, rerun the same seed and long-run program directly from `main` without source extraction. A mismatch between that run and this result invalidates this result as canonical replay evidence.

Machine-readable evidence:

`validation/results/long_architecture_falsification_20260826_local.json`
