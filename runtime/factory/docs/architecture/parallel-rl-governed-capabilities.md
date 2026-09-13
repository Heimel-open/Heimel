# Parallel-RL governed capabilities

Status: adopted Factory research-backed pattern
Owner: nsolland
Research basis: arXiv:2608.03573, *SFT Conflicts, RL Coexists: A Theoretical and Empirical Analysis of Multi-Task Learning for LLMs* (2026-08-04).

## Evidence boundary

The paper reports that, in its evaluated multi-task settings, RL updates are sparse and approximately orthogonal across tasks while SFT exhibits stronger task interference under multi-stage training. The authors use this result to motivate Parallel-RL: train task capabilities independently and compose them later.

VALO adopts the architectural implication, not a universal safety claim. Sparse or near-orthogonal updates do not by themselves prove that arbitrary capability deltas can be merged safely. Every trained capability and every composition remains a candidate until independently evaluated and admitted.

## Factory pattern

`one admitted base -> independent RL capability jobs -> versioned capability candidates -> independent evaluation -> governed composition candidate -> new admission/promotion decision`

Each capability job is isolated by purpose and task scope. It produces a candidate artifact only. Composition never grants authority and never bypasses evaluation.

## Capability artifact

A Parallel-RL capability candidate must preserve at least:

- capability id and version;
- base model identity/digest;
- governed workspace and purpose;
- dataset and provenance digests;
- reward/objective specification digest;
- training engine identity, runtime digest and attestation;
- resulting capability/delta digest;
- held-out evaluation and negative-test receipt digests;
- compatibility/composition constraints;
- admissibility state.

The artifact is immutable and versioned. Re-training creates a new candidate; it does not mutate an admitted capability in place.

## Composition contract

A composed model is a new artifact, not merely the sum of previously admitted capabilities.

Before promotion, the composition must be evaluated for:

1. preservation of each intended capability;
2. cross-capability interference and regressions;
3. out-of-scope behavior and negative cases;
4. conformance with the governed workspace;
5. provenance and complete capability lineage;
6. current admissibility under the target purpose and deployment context.

A clean result for each capability in isolation is necessary but not sufficient for composition admission.

## Authority invariant

Capability is not authority.

Training or composing a model changes what it may be able to do. It does not change what it is permitted to do. Runtime execution remains governed by current state, purpose, scope, evidence and authority through the canonical chain:

`VAIG -> reht -> RACS -> external PEP -> execution -> Veritas`

No training engine, capability artifact, merge operation, benchmark score or model confidence can create, widen or persist execution authority.

## Promotion and rollback

Promotion is explicit and receipt-backed. A candidate capability or composed model must cross a fresh admission/promotion boundary before becoming operative.

Because capabilities are tracked as separate versioned artifacts, VALO can revoke, replace or roll back a capability lineage without treating the whole model-development history as one opaque training event. Rollback remains an artifact-management operation; any subsequent execution still requires fresh runtime authorization.

## Relation to governed skill distillation

Parallel-RL complements governed skill distillation. Distillation moves reusable competence into cheaper/smaller artifacts; Parallel-RL provides a research-backed way to keep independently trained capabilities separable during development and composition.

Both preserve the same boundary:

`learning transfers capability; learning never transfers authority`
