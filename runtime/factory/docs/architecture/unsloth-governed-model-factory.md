# Governed model factory: Unsloth adapter

Status: implemented
Owner: nsolland
Branch: `codex/unsloth-governed-provider-v1`
Canonical base: `860dbbb9d17a7e5811b9487c8399c28184b25aee`
Unsloth fork: `nsolland/unsloth@993e3e4529fc5796ef945d8c2b5af7b75ccfbf4f`
Contract: `valo.governed-model-factory.v1`

## Boundary

Unsloth is a replaceable training engine inside VALO Factory. It is not a governance component and it cannot create authority, admit state, select operative truth, authorize execution, retry work, or promote a trained model.

The authoritative sequence remains:

`admitted state + governed workspace -> VAIG -> reht -> RACS -> PEP -> replaceable training engine -> candidate artifact -> new admission/promotion decision`

The engine receives only a bounded work unit that has already crossed the state-admission and execution-governance boundaries.

## Required bindings

`lib/unsloth_factory.py` requires:

- governed workspace identity, purpose, workspace digest and authority receipt;
- admitted state digest, admission receipt and provenance chain;
- an explicit `VAIG -> reht -> RACS -> PEP` receipt chain;
- a runtime engine identity bound to repo, exact commit, runtime digest and attestation receipt;
- a training specification bound to a dataset digest;
- `attempt=1`, retry policy `none`, and candidate-only output.

A token may authenticate access to infrastructure outside this contract. It is never an authority source and is not included in the handoff or its digest.

## Replaceable engine

The current convenience builder pins:

`nsolland/unsloth@993e3e4529fc5796ef945d8c2b5af7b75ccfbf4f`

The governance contract itself is engine-neutral. Replacing Unsloth changes the engine identity and runtime attestation, not the governed workspace, admitted state, authority, purpose or governance receipts.

## Parallel-RL capability jobs

The model factory may use the same governed training handoff for independent RL capability jobs. Each job remains purpose-bounded and candidate-only; the training engine does not compose or promote capabilities.

Research basis: arXiv:2608.03573 reports sparse and approximately orthogonal RL updates across tasks in its evaluated settings and proposes Parallel-RL, where task training is decoupled before later composition.

VALO preserves the evidence boundary: this result supports independent capability training but does not establish that arbitrary deltas are automatically safe to merge.

Composition is therefore a separate governed artifact step implemented by `lib/parallel_rl.py` under contract `valo.parallel-rl-composition.v1`. It requires versioned capability lineage, shared base-model identity, individual evaluation evidence, negative/compatibility receipts and a composition evaluation plan. The result is always `CANDIDATE_REQUIRES_EVALUATION` and requires a new admission/promotion decision.

Capability is not authority. A new or composed capability cannot widen execution authority; live execution still requires current authorization through VAIG -> reht -> RACS -> PEP.

## Runtime attestation

A git SHA alone is insufficient. The handoff also requires a 256-bit runtime digest and an attestation receipt. The PEP handoff carries that exact digest so the runtime that executes can be checked against the runtime that was authorized.

If the runtime digest or attestation is missing or malformed, the adapter fails closed.

## No hidden retries

The adapter permits exactly one execution attempt. Retry counters and retry controls are rejected from the request and training parameters. Any retry is a new governed work unit requiring fresh admissibility under current state and authority.

## No automatic promotion

Training produces a candidate only. `push_to_hub`, `auto_publish`, `auto_promote` and equivalent control fields are rejected. A candidate must cross a new admission/promotion boundary before it can become operative.

## Optional external media adapter

Njål Hansens media pipeline may be attached as an optional external adapter. Its digest is preserved for provenance, but the adapter is explicitly non-authoritative and cannot alter the governance chain or grant execution authority.

VALO Factory therefore does not depend on that media pipeline, on Unsloth, or on any particular external training/runtime provider.

## CLI

`bin/valo-unsloth` validates one governed JSON request and emits the deterministic PEP handoff.

```bash
bin/valo-unsloth --request governed-training.json --dry-run
```

The CLI does not execute training. A real PEP/runtime adapter consumes the validated handoff and remains responsible for enforcement and runtime attestation.

## Conformance

`tests/test_unsloth_factory.py` contains 17 offline tests covering:

- canonical deterministic encoding;
- governed workspace and state admission;
- provenance;
- runtime digest and attestation;
- fixed VAIG -> reht -> RACS -> PEP ordering;
- fail-closed non-ALLOW outcomes;
- no hidden retries;
- no token-derived authority;
- no automatic promotion;
- optional non-authoritative media adapter;
- engine replaceability;
- JSON CLI dry-run.

`tests/test_parallel_rl.py` adds composition-level conformance for capability lineage, evidence completeness, candidate-only promotion and no authority transfer.
