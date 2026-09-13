# Paired Governance Benchmark v1 — Frozen Evidence Snapshot

Status: **FROZEN**

This file fixes the exact internal conformance-evidence snapshot. Later stress, reproduction, external-environment, or multi-model work must not silently redefine the v1 result.

## Frozen benchmark snapshot

- repository: `nsolland/valo-reht`
- benchmark branch at freeze: `eval/paired-governance-benchmark-v1`
- frozen benchmark commit: `e6cbf21138d3f78a794a485aafa34f826e196361`
- scenario-set blob: `77dccaabde3deb0b35cab51c893007b338b6e217`
- scenario count: `15`
- Python: `3.12`

## Pinned execution-chain dependencies

- `valo-workflow-isa`: `6e5b3633f17bdb150fb2b6118a44b4186d4926ba`
- `valo-kernel`: `d96afcc97a4fa5daea837b52945b266b3cd6b432`
- `action-attestation-service`: `1b52dcbac4646ec37694329372881008a6bec43b`
- `valo-gateway`: `dbfdae75fa44b4a58b9622289953817378268be2`
- `valo-platform`: `332cd74d26f161addc4eaa1cad2c2013e5c7d54e`
- `Racs`: `e5ad82a629425ee2725297b32eef9173f2542d64`
- `Veritas`: `abc6138e3f3d80fffdd95878f6ac0c1dd053ffa5`

## Frozen observed result

| Metric | CONTROL | Governed chain |
|---|---:|---:|
| correct completion | 13.3% | 100.0% |
| unsafe commit | 86.7% | 0.0% |
| interception | 0.0% | 100.0% |
| false block | 0.0% | 0.0% |
| bypass | 100.0% | 0.0% |
| null-effect violation | 0.0% | 0.0% |
| evidence closure | 0.0% | 100.0% |

Instrumented CI run 176 measured:

- REHT authorization: `0.063 ms p50`, `0.124 ms p95`
- full governed chain: `2.217 ms p50`, `4.109 ms p95`
- `154 passed, 1 skipped`
- CI: success
- Assurance Release Gate: success

## Claim boundary

This frozen snapshot is **internal deterministic conformance evidence**, not a universal safety or universal performance claim. It establishes the result for the pinned scenario set and pinned component chain above.

Subsequent internal stress testing may strengthen confidence in repeatability, determinism, concurrency behavior, invariant preservation, and latency distributions. Multi-model and independent external reproduction remain separate later phases.
