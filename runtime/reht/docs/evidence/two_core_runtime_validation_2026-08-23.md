# TWO-CORE Runtime Validation against the frozen REHT regime — 2026-08-23

Repository: `nsolland/valo-reht`
Branch: `refactor/two-core-runtime`
Date: 2026-08-23

## Purpose

Validate the new authoritative runtime path

```
Kernel state/context
  -> RealReht
  -> minimal mechanical effect adapter
  -> outcome evidence
  -> Kernel observation/admission
```

against the previously frozen governance regime. The old chain

```
Kernel -> REHT -> RACS -> Gateway -> Veritas
```

was NOT reconstructed. Instead the two-core path is exercised end to end with a
TEST-ONLY mechanical effect adapter (no new production layer).

## Start and final SHAs

- Start SHA (branch base before this task): `ec3e1a8aaf6e504ed203144b62e1e00a6dac8925`
- Final validated state SHA (last code/bench commit): `d048ddf0e26b9e5f80e2d2d854cd15b4ebbba23b`
- This evidence report is recorded on top of that state as the branch's final commit.

The task synced `origin/main` (advanced to `d9001145f67c1e7433d6ec4784877436529abf86` after PR #36) into the work branch with `git merge --no-ff origin/main`. No conflict.

## Commits created by this task

| SHA (short) | Message |
|---|---|
| `3734aae` | Merge branch 'main' into refactor/two-core-runtime (no-ff) |
| `e0047cd` | contract: narrow REHT decision plane to ALLOW | STEP_UP | DENY |
| `b811e7d` | test: two-core runtime regression across frozen governance families |
| `69b327c` | bench: add two-core latency measurement and record same-machine old vs new |
| `3461ee3` | test: two-core permit single-use smoke under concurrency |
| `979d77f` | bench: wrap method string for ruff line length |
| `68abd84` | bench: record frozen real-REHT paired run after two-core changes |
| `d048ddf` | bench: refresh two-core latency record from final run |
| (final commit) | docs: two-core runtime validation evidence 2026-08-23 |

## Files changed

- `src/valo_reht/contracts.py` — DecisionResult decision type narrowed to `Literal["ALLOW", "STEP_UP", "DENY"]` with construction-time validation.
- `src/valo_reht/reht.py` — removed the stale "wider outcome plane" (MODIFY/DEFER/HALT) doc text; documented the exact decision plane.
- `tests/test_reht_decision_contract.py` — new: ALLOW/STEP_UP/DENY accepted; MODIFY/DEFER/HALT rejected.
- `tests/two_core_harness.py` — new TEST-ONLY two-core harness (Kernel fixture builders, mechanical effect adapter, outcome evidence, Kernel observation, runtime driver).
- `tests/test_two_core_runtime.py` — new: frozen-family two-core regression suite (15 families + aggregate PASS).
- `tests/test_two_core_concurrency_smoke.py` — new: cheap single-permit concurrency/replay smoke (12 workers, 1 race; not the 25x16/400 stress).
- `benchmarks/paired_governance/run_two_core_latency.py` — new: two-core latency measurement.
- `benchmarks/paired_governance/latest_two_core_latency.json` — measured output.
- `benchmarks/paired_governance/latest_latency_breakdown.json` — same-machine old-chain comparison (from the existing benchmark).
- `benchmarks/paired_governance/latest_real_reht_results.json` — frozen real-REHT paired run re-run locally.

## Test commands and results

Targeted (FASE 1):
```
.venv/bin/python -m pytest tests/test_reht_decision_contract.py tests/test_reht.py tests/test_reht_step_up.py -q
32 passed in 1.45s
```

Two-core regression (FASE 2):
```
.venv/bin/python -m pytest tests/test_two_core_runtime.py -q
18 passed in 5.37s
```

Concurrency smoke (FASE 4):
```
.venv/bin/python -m pytest tests/test_two_core_concurrency_smoke.py -q
1 passed in 2.75s
```

Full local suite (FASE 5, only after the above were green):
```
.venv/bin/python -m compileall -q src tests         # OK
.venv/bin/python -m ruff check src tests            # All checks passed!
.venv/bin/python -m pytest -q                        # 191 passed, 1 skipped in ~10-14s
```

The single skip is pre-existing: `tests/test_security_assurance_release_gate.py:36`
("exact dependency snapshots are loaded by the release workflow"). No material
integrity regression.

CI-equivalent ruff over benchmarks also passes with the documented
`--ignore I001` per-file ignore (`run_end_to_end.py`).

Actual runtime: well under the FASE 1-4 budget. Full pytest ~10-14 s.

## Scenario results (two-core regression)

All 15 required scenario families exercised through
`Kernel state/context -> RealReht -> mechanical effect adapter -> evidence -> Kernel`:

| Scenario | Oracle | Actual | Effect committed |
|---|---|---|---|
| valid authorized action | ALLOW | ALLOW | yes (once) |
| missing identity | DENY | DENY | no |
| missing authority | DENY | DENY | no |
| revoked authority at commit | DENY | DENY | no |
| expired authority | DENY | DENY | no |
| scope mismatch | DENY | DENY | no |
| purpose mismatch | DENY | DENY | no |
| constraint mismatch | DENY | DENY | no |
| stale Kernel state/context | DENY | DENY | no |
| action substitution | DENY | blocked by adapter | no |
| material state change before commit | DENY | blocked by adapter | no |
| direct-effect bypass | DENY | blocked (no permit) | no |
| permit replay / single-use | DENY | second use blocked | exactly one |
| governed consequential state/memory write | DENY | DENY | no |
| STEP_UP requirement | STEP_UP | STEP_UP, no permit | no |

Aggregate PASS criteria (asserted in `test_two_core_aggregate_*` and individual tests):

- unsafe commits = 0
- bypass = 0
- permit replay effects = 0 (single-use)
- false authority creation = 0 (Kernel authority set unchanged after commit + evidence)
- all negative authority/freshness cases fail closed
- evidence closure = 100% for committed effects (decision + permit + ctx hash + action digest + observation event)

## Direct-effect / replay result

- Mechanical effect adapter requires an exact REHT permit/binding; a direct effect
  without a permit is denied (PG-010 / dedicated adapter test).
- A consumed permit cannot commit a second effect (PG-012 / replay tests).
- Concurrency smoke: one fresh permit raced by 12 concurrent commit attempts
  produced exactly 1 committed effect and 11 replay denials.

## Latency (old vs new)

Methodology: `perf_counter_ns`, p50/p95/p99 via sorted linear interpolation, same
frozen 15-scenario families. Old-chain numbers were produced locally by the
existing `run_latency_breakdown.py` on the same machine for a same-machine
relative comparison.

| Path | p50 (ms) | p95 (ms) | p99 (ms) | max (ms) |
|---|---|---|---|---|
| NEW REHT-only (per call) | 0.489 | 0.582 | 0.621 | 0.736 |
| NEW TWO-CORE end-to-end (per scenario) | 19.05 | 34.55 | 54.09 | 76.78 |
| OLD REHT layer (same machine) | 0.409 | 1.157 | — | 1.262 |
| OLD full chain (same machine) | 23.24 | 53.18 | — | 87.53 |

Frozen GitHub Actions baselines for reference (different hardware):
OLD REHT p50 ~0.049-0.063 ms, p95 ~0.124 ms; OLD full chain p50 ~2.1-2.2 ms,
p95 ~3.8-4.1 ms.

**NOT DIRECTLY COMPARABLE to the frozen CI baselines.** The local machine is not
the GitHub Actions runner, and the two-core measurements use the newer canonical
`valo-kernel` (b72c717) whose context/state path is heavier than the one used in
the frozen CI latency run. The useful, honest comparison is the same-machine one:
- NEW two-core per-scenario (19.05 ms) is lower than OLD full chain per-scenario
  (23.24 ms) on the same machine — consistent with removing RACS/Gateway/Veritas
  layers from the executed path while keeping Kernel context + REHT + evidence.
- REHT-only is materially unchanged (0.49 vs 0.41 ms same-machine).

Conclusion on latency: same-or-better within local methodology; do not claim a
global speedup against the frozen CI numbers because the environments differ.

## Answers to the seven questions

1. **Safety semantics preserved?** Yes. All negative authority/freshness families fail closed; unsafe commits = 0; null-effect violations = 0.
2. **Authority semantics preserved?** Yes. Missing/expired/revoked/out-of-scope/out-of-purpose/constraint-breached authority all DENY; the mechanical adapter cannot mint authority (Kernel authority set unchanged).
3. **NO_DIRECT_EFFECT_PATH preserved?** Yes. The mechanical effect adapter requires an exact REHT permit; direct effects without a permit are denied, and action substitution after authorization is rejected.
4. **Replay/single-use preserved?** Yes. A consumed permit cannot commit again; concurrency smoke commits exactly once under 12 simultaneous attempts.
5. **Evidence closure preserved?** Yes. Committed effects carry decision + permit + ctx hash + action digest + Kernel observation event; 100% closure.
6. **Latency better/equal/worse?** Same-or-better on a same-machine basis (NEW two-core 19.05 vs OLD full chain 23.24 ms per scenario; REHT-only unchanged). NOT DIRECTLY COMPARABLE to frozen CI baselines.
7. **Old runtime dependencies no longer needed?** RACS, Gateway, Veritas and the containment/`valo-platform` egress gate are no longer on the authoritative runtime path. They remain as external assurance fixtures only for cross-system conformance/benchmark coverage while the two-core consolidation lands (see `repo-manifest.yaml` / `.github/workflows/ci.yml`). `valo-workflow-isa` is already removed by the branch. `valo-kernel` remains the single canonical runtime dependency.

## Blockers

None. No merge performed (per protocol, PR #37 is intentionally not merged).

## Final statement

AUTHORITATIVE RUNTIME = KERNEL + REHT