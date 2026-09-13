# VALO Workflow ISA Wave 1 producer audit

Status: `WORKFLOW_REPAIR_READY_FOR_INDEPENDENT_QC` (producer result only)

Audited against:

- Index hardening baseline: `nsolland/Index@2f92d1028c54f7667382bafed81d5271ffe58f26`
- Workflow ISA audited base: `nsolland/valo-workflow-isa@9d53e667bb1f1881ff8010210acb6c974133f575`
- Reproduced Kernel dependency: `nsolland/valo-kernel@edf39cc914843e763c4385c0024d775c7458e1e8`

The producer did not assign `HARDENED`, did not mutate the Index or an external
consumer repository, and did not merge this work.

## Findings

| ID | Invariant / path | Producer evidence and bounded repair | Classification | Independent minimum action |
| --- | --- | --- | --- | --- |
| WORKFLOW-COMPILE-001 | Every graph must compile before any runtime or Gateway execution, and a compile result must be bound to exact graph content. | The cache was keyed only by graph ID, so a valid graph could prime a same-ID invalid WRITE graph; direct `run` also skipped compilation. The cache now uses the canonical graph digest, and `start`, `run`, `resume`, and child calls enforce compilation. Negative tests prove both bypasses stop before Gateway execution. | `FAIL` (repaired in this PR) | Reproduce both same-ID cache collision and direct-public-`run` paths on the exact PR head. |
| WORKFLOW-WAIT-001 | Native `WAIT` must deterministically defer and resume from supplied input. | Readiness filtering skipped a pending native `WAIT`, producing `FAILED: no ready nodes`. Native `WAIT` now executes, emits defer state, and resumes to completion with the injected value. | `FAIL` (repaired in this PR) | Reproduce native `ControlOpcode.WAIT` defer/resume through the public runtime. |
| WORKFLOW-RETRY-001 | An ambiguous irreversible WRITE outcome must neither replay blindly nor become verified/completed from Gateway detection alone. | A lost response after external execution caused `GatewayPort.has_effect` to produce `EffectVerified` and completion without Veritas observation, a Kernel event, or node output. Detection now stops replay and yields `DEFERRED` with `outcome_known=false`; it emits no `EffectVerified`, creates no Kernel transition/output, and performs one external call. Generic `resume` input cannot re-arm the deferred WRITE. | `FAIL` (repaired in this PR) | Reproduce the response-loss and attempted-resume paths and independently prove the absence of replay, verified-effect evidence, Kernel transition, and authoritative output. |
| WORKFLOW-RECONCILIATION-001 | A deferred ambiguous WRITE needs a governed positive reconciliation/continuation path. | This repair deliberately supplies no new evidence authority or continuation architecture. The runtime fails closed in `DEFERRED`; a trustworthy external reconciliation artifact and governed continuation contract remain a system/integration dependency. | `CAPABILITY_GAP` | Define ownership and an independently verifiable reconciliation artifact before adding any continuation path. |
| WORKFLOW-BINDING-001 | A RACS execution binding must deterministically bind the fresh REHT decision to the exact action contract and execution context. | The prior binding used only one decision reference, so distinct actions produced the same binding and stale/missing context hashes were accepted. The binding now digests the full decision fields plus complete action contract; `ALLOW` requires a decision reference and the exact fresh execution-context hash. Negative tests fail before Gateway on missing/mismatched artifacts. | `FAIL` (repaired in this PR) | Independently vary action content, context hash, and decision references and verify fail-closed behavior. |
| WORKFLOW-MODIFY-001 | `MODIFY` must never execute the original action as though it were the modified action. | The prior runtime accepted `MODIFY` and sent the original action to Gateway. The unsafe executable path is closed: every `MODIFY` is denied before Gateway. | `FAIL` (repaired in this PR) | Reproduce `MODIFY` through the public WRITE path and prove the original action never reaches Gateway. |
| WORKFLOW-MODIFY-CAPABILITY-001 | A future positive `MODIFY` continuation must carry the exact governed modified action. | `DecisionResult` cannot represent the exact modified action contract. This repair adds no substitute field or architecture; positive `MODIFY` continuation remains unavailable while the runtime fails closed. | `CAPABILITY_GAP` | Define ownership and govern an exact modified-action artifact before enabling positive continuation. |
| WORKFLOW-PERSISTENCE-001 | Workflow state/events must be durably recoverable in a production integration. | `RuntimeBackend` is the locatable ownership seam and `ReferenceBackend` is intentionally in-memory. A durable backend is by design a system/integration capability dependency, not evidence of a Workflow ISA contract defect or missing ISA ownership. | `CAPABILITY_GAP` | Provide and independently verify the external durable runtime/backend integration against the existing contract. |
| WORKFLOW-EFFECT-001 | Every consequence-bearing Workflow ISA entry point and downstream effect surface must be enumerated and closed. | Compile, WRITE-handler, Gateway, Veritas, Kernel-event, and retry entry points are locatable in this repository. What remains missing is independent cross-repository effect-surface evidence across REHT, RACS, Gateway, Veritas, and Kernel consumers. | `UNVERIFIED` | Independently trace the exact-head cross-repository effect surface; do not infer closure from local tests alone. |

## Adversarial reproduction

On the audited base, the producer reproduced these concrete failures before
repair:

- native `WAIT` failed with `no ready nodes and terminals not reached`;
- a same-ID compile-cache collision executed an invalid WRITE at Gateway;
- a directly constructed invalid instance reached Gateway through public `run`;
- an ambiguous response-loss retry completed with `EffectVerified` despite no
  Veritas result, Kernel event, or execution output;
- distinct action contracts produced the same execution binding; and
- REHT `MODIFY` executed the original action contract.

The repaired tree adds real-path negative coverage for each executable bypass.
The full suite passes with the exact reproduced Kernel dependency anchor.

## Producer checks

Executed from the Workflow ISA tree:

```text
python -m pytest -q
python -m compileall -q src tests examples
ruff check src tests examples
ruff check .
git diff --check
```

Producer result: `92 passed`. All compile, lint, and whitespace checks passed.
The same full suite also passed with
`nsolland/valo-kernel@edf39cc914843e763c4385c0024d775c7458e1e8`
placed first on the dependency path.

All commands and adversarial paths must be rerun against the frozen exact PR
head by an independent verifier. The producer context does not attest the
final result.
