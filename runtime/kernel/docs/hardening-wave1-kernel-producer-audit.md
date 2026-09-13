# VALO Kernel Wave 1 producer audit

Status: `KERNEL_TAXONOMY_AMENDMENT_READY_FOR_QC` (producer result only)

Audited against:

- Index hardening baseline: `nsolland/Index@2f92d1028c54f7667382bafed81d5271ffe58f26`
- Kernel audited base: `nsolland/valo-kernel@3d87c67fc57682a03539361bef033a1e22e6764c`
- Independent QC: [`PASS — KERNEL_REPAIR_VERIFIED`](https://github.com/nsolland/valo-kernel/pull/30#issuecomment-5301751422), comment `5301751422`, exact verified head `nsolland/valo-kernel@3f2e6a8f08beabcfe60ebb7fa87a7b2d0afbd676`

The producer did not assign `HARDENED` and did not merge this work.

## Findings

| ID | Invariant / path | Result | Classification | Minimum action |
| --- | --- | --- | --- | --- |
| KERNEL-REPLAY-001 | Event/hash-chain integrity must hold for deterministic replay and historical reads. `replay`, `replay_at`, and `state_effective_at` reduced supplied events without first verifying the complete chain. | A tampered sealed event was reduced into attacker-controlled state. | `FAIL` (repaired in this PR) | Verify the complete chain before any replay or bitemporal filtering; add a real-path negative test. |
| KERNEL-WORKSPACE-001 | Governing contract drift after workspace compilation must not continue to execution. | Amendment changes a dependency digest and yields `GOVERNING_CONTRACT_DRIFT → DEFER`; termination is rejected at compilation. | `UNVERIFIED` pending independent QC | Independently reproduce on this exact head. |
| KERNEL-ADMISSION-001 | Evidence admission must be VALO-owned, reproducible, tenant-bound, and fail closed. | Dedicated admission and bypass tests pass on the audited tree; quarantine, hold, reject and admit paths are represented. | `UNVERIFIED` pending independent QC | Independently reproduce all outcomes, including quarantine. |
| KERNEL-TENANT-001 | Cross-tenant state and references must not enter authoritative state. | Event tenant checks, object tenant checks, and relationship/reference negative tests pass. | `UNVERIFIED` pending independent QC | Exercise alternate pack and workspace paths independently. |
| KERNEL-STATE-001 | Authoritative state must be append-only/reducer-owned and externally returned state must not mutate it. | Public `state()` returns a deep copy and append is the documented mutation boundary. | `UNVERIFIED` | Independent effect-surface audit must establish all reachable stores/write paths. |
| KERNEL-PERSISTENCE-001 | Persistent bytes/state must remain bound to admitted evidence and governed workspace context. | The binding validator exists and fails closed. Kernel provides the storage-agnostic contract and `MemoryStore`; durable persistence is by design external to Kernel, so the absent durable integration is not evidence of a Kernel contract defect. | `CAPABILITY_GAP` | Treat durable persistence as a system/integration capability dependency; provide and verify the external store/runtime integration without assigning it to Kernel ownership. |
| KERNEL-EFFECT-001 | All consequence-bearing state writes and execution-bound outputs must be enumerated and closed. | `KernelEngine.state()` deep-copy behavior, the append/reducer path, and `MemoryStore` make the Kernel implementation/write surface locatable. What remains missing is independent cross-repository effect-surface evidence across REHT, RACS, Gateway, and Veritas consumers. | `UNVERIFIED` | Independently trace and verify the external consumer effect surfaces across REHT, RACS, Gateway, and Veritas. |

## Adversarial coverage

The audited tree contains runtime-path tests for candidate/workspace binding,
workspace expiry and relevant-state drift, governing-contract amendment and
termination, evidence admission bypass, tenant isolation, replay/idempotency,
authority revocation, delegation narrowing, stale evidence, and execution
context freshness. The producer additionally tests tampered event payload
replay through the public `replay` function.

The taxonomy amendment itself still requires exact-head independent QC. The
external durable-persistence system/integration capability and complete
cross-repository effect-surface closure at REHT, RACS, Gateway/PEP, and Veritas
boundaries remain outside a producer claim of completion.

## Exact commands

Executed from the audited Kernel tree:

```text
python -m pytest -q
python -m pytest -q tests/test_hardening_wave1.py tests/test_governing_contract_drift.py tests/test_workspace.py tests/test_admission.py
python -m compileall -q src tests
ruff check .
git diff --check origin/main..HEAD
```

All commands are expected to be rerun against the final PR head by an
independent verifier. The producer context does not attest the final result.
