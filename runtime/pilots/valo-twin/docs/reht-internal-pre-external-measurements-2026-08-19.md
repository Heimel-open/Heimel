# reht Internal Pre-External Measurements — 2026-08-19

Status: INTERNAL BASELINE / NOT A PRODUCTION LATENCY CLAIM

This record freezes what can be measured inside the current deterministic TypeScript/reference implementation before external model-backed and production-I/O testing.

## Scope

Measured on GitHub-hosted Ubuntu 24.04 runners with Node 20.20.2. The benchmark intentionally excludes model inference, network calls, external registries, databases, WORM persistence, HSM/signature operations and real consequence-bearing effectors.

The measurements therefore isolate deterministic/reference computation. They MUST NOT be represented as end-to-end production reht latency.

Benchmark source: `src/lib/rehtInternalLatencyBenchmark.test.ts`.

## Green validation

Two consecutive executions on separate hosted runners completed successfully:

- workflow run `32246619804`, first successful attempt/job `96048434799`;
- workflow run `32246619804`, re-run job `96048807779`.

Both completed:

- TypeScript check: PASS;
- lint: PASS;
- test suite: **188 / 188 PASS**;
- build: PASS.

## Deterministic benchmark results

| Measurement | Green run A | Green run B | Mean |
|---|---:|---:|---:|
| Standing authority ALLOW evaluation | 96.4 ns/op | 92.9 ns/op | 94.65 ns/op |
| v1 hard-conformance case evaluation | 132.4 ns/op | 103.5 ns/op | 117.95 ns/op |
| Build full 2,976-cell v2 publication plan | 32.043 µs/plan | 30.645 µs/plan | 31.344 µs/plan |
| Score complete 96-cell model-free corpus | 66.340 µs/corpus | 67.305 µs/corpus | 66.823 µs/corpus |

Derived from the two green runs:

- authority evaluation throughput: approximately **10.37–10.76 million evaluations/s**;
- v1 conformance evaluation throughput: approximately **7.55–9.66 million cases/s**;
- v2 plan construction: approximately **31.2–32.6 thousand complete 2,976-cell plans/s**;
- v2 96-cell scoring: approximately **14.9–15.1 thousand complete corpora/s**;
- mean v2 scoring cost per cell, dividing whole-corpus scoring by 96: approximately **0.696 µs/cell**.

These are microbenchmarks of the current implementation and include JIT/runtime effects. They establish only that deterministic local computation is not presently the dominant latency concern.

## Existing semantic coverage retained

The green suite includes current PEACE/reht tests for standing/authority, reciprocal standing, sustainability trajectory, constitutional jurisdiction, registry behavior, state replication, continuity/Framleis compatibility, v1/v2 conformance, replay, bypass and mutation/fail-closed semantics.

Hard-conformance policy remains unchanged:

```text
critical escaped effects = 0
boundary bypasses = 0
unreceipted admitted effects = 0
```

No latency result can compensate for a hard-conformance failure.

## What remains unmeasured internally

The current repo cannot establish production end-to-end latency for:

1. external authority/standing state resolution;
2. remote registry/policy/evidence access;
3. database transaction / CAS latency;
4. cryptographic signing and verification;
5. WORM / receipt persistence;
6. network path to a real effector;
7. real payment, cloud, industrial or other consequence commit;
8. model inference and model-provider variance;
9. hardware/edge-specific performance;
10. multi-region or degraded-network behavior.

Those belong to later integrated and external profiles.

## Interpretation

The internal evidence supports the narrow statement:

> **The current deterministic reht/PEACE decision and conformance computation is computationally small relative to the external I/O and model latency expected in a production path.**

It does not yet support a numeric production claim such as “reht adds X ms.”

The next benchmark stage should separately measure local-state, remote-state and production-effector profiles and report p50/p95/p99 rather than only means.
