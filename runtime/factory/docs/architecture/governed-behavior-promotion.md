# Governed behavior promotion and rollout

Status: architecture adopted; implementation tracked in issue #32.

## Purpose

Factory OS governs how a validated behavior patch may move from Research Factory into shadow, canary and active use.

A behavior specification, evaluation result, repository merge or agent consensus is evidence only. None creates activation authority by itself.

## Boundary

Research Factory owns candidate generation, challenge, evaluation and validation through `PROMOTION_REQUESTED`.

Factory OS owns:

- promotion intake;
- authority and policy verification;
- exact scope and target binding;
- risk classification;
- separation of duties;
- bounded rollout missions;
- shadow and canary stages;
- scoped activation;
- runtime observation intake;
- quarantine and exact rollback;
- activation and lifecycle receipts.

Factory OS does not decide whether a concrete user or system action is allowed. Consequence-bearing actions remain behind VAIG, REHT, RACS and Core enforcement.

## Canonical flow

```text
validated BehaviorPatchV1
→ BehaviorPromotionRequestV1
→ verify exact digests, principal, authority, scope, target and expiry
→ classify rollout risk
→ issue bounded mission
→ SHADOW
→ CANARY
→ ACTIVE
→ observe
→ remain active | QUARANTINED | ROLLED_BACK | RETIRED
→ receipt chain
```

## Required intake

Promotion intake must bind and verify:

- `BehaviorSpecRefV1`;
- `BehaviorPatchV1`;
- `BehaviorEvaluationV1`;
- `BehaviorPromotionRequestV1`;
- base repository and commit SHA;
- exact behavior file digest;
- exact requested agent, role, workflow, repository or organization scope;
- environment;
- principal and authority basis;
- policy version;
- expiry;
- shadow and canary requirements;
- exact rollback target.

Any material mismatch fails closed.

## Rollout lifecycle

```text
REQUESTED
→ AUTHORIZED
→ SHADOW
→ CANARY
→ ACTIVE
→ QUARANTINED | ROLLED_BACK | RETIRED
```

Invalid paths:

- `REQUESTED → ACTIVE`;
- `SHADOW → ACTIVE` where canary is required;
- `QUARANTINED → ACTIVE` without fresh validation and authorization;
- rollback to an unknown, unvalidated or unauthorized digest.

## Separation of duties

For consequential behavior changes:

- the proposer cannot validate the patch alone;
- the implementing worker cannot approve its own rollout;
- the evaluator cannot activate its own result;
- QC cannot change code, behavior files or rollout policy;
- the promoter cannot self-attest successful activation;
- the runtime observer may submit regression evidence but cannot choose a replacement version.

Existing Factory OS claim, mission, QC, head-SHA and receipt controls must be reused.

## Risk classification

Behavior rollout risk is separate from ordinary code-change risk.

### Class A

Narrow, reversible, non-consequential behavior changes that do not affect authority, policy interpretation, credentials, tool access or execution boundaries.

May enter shadow automatically after validated intake. Activation still requires the configured promotion authority.

### Class B

Shared role or workflow behavior affecting production quality, cost, user experience or operational reliability without changing authority boundaries.

Requires independent evaluation, canary evidence and double control.

### Class C

Any behavior touching or plausibly affecting:

- authority or delegation;
- REHT or RACS semantics;
- credential scope;
- policy loading or interpretation;
- no-bypass invariants;
- self-attestation;
- destructive or externally consequential execution;
- organization-wide propagation.

Class C requires explicit human authority and cannot auto-activate.

## Scope monotonicity

A promotion request is valid only for its declared scope.

Scope expansion is never implicit:

```text
named agent ≠ role
role ≠ repository
repository ≠ organization-wide
```

Promotion to a broader scope requires new evaluation and authority. A valid local rollout cannot be reused as a global authorization.

## Shadow and canary

Shadow mode evaluates the new behavior without allowing it to control consequential execution.

Canary mode activates the behavior only for the explicitly authorized bounded population, workflow or environment.

Both stages must bind:

- behavior digest;
- repository and commit SHA;
- target scope;
- environment;
- policy version;
- observation window;
- success and rollback thresholds;
- receipt chain.

## Activation

Activation requires:

- valid, unexpired promotion request;
- exact validated patch and evaluation digests;
- matching base behavior digest;
- matching target scope and environment;
- required authority;
- successful mandatory shadow and canary gates;
- valid QC and CI evidence where repository changes are involved;
- no policy or no-bypass regression;
- a receipt-bound activation record.

A merged `BEHAVIOR.md` remains inactive until these conditions are met.

## Observation and quarantine

Runtime observation may report:

- outcome regression;
- trajectory regression;
- boundary or authority regression;
- unsafe tool use;
- recovery failure;
- resource-cost regression;
- scope leakage;
- contradictory or harmful behavior interaction;
- receipt or target mismatch.

Bounded policy may quarantine automatically when evidence crosses a configured threshold.

Quarantine removes the affected exact behavior version from active use. It cannot select, validate or activate a replacement.

## Rollback

Rollback may restore only an exact previously validated and authorized behavior digest for the same compatible scope and environment.

Rollback must emit a receipt binding:

- failed active digest;
- restored digest;
- triggering evidence;
- principal or bounded system authority;
- target scope;
- environment;
- policy version;
- commit SHA;
- time and sequence;
- previous receipt hash.

## Receipts

Factory OS emits at least:

- promotion acknowledgement;
- authorization decision;
- shadow start and result;
- canary start and result;
- activation;
- observation linkage;
- quarantine;
- rollback;
- retirement.

Receipts prove what Factory OS authorized and changed. They do not prove that a behavior is universally correct or that a later agent action was authorized.

## Mandatory invariants

1. A behavior file is not authority.
2. Validation is not activation.
3. Repository merge is not activation.
4. Active behavior is not execution clearance.
5. The worker cannot approve its own rollout.
6. The evaluator cannot activate its own result.
7. Scope expansion invalidates prior authorization.
8. Changed base, patch, evaluation or behavior digest invalidates the request.
9. Class C behavior cannot auto-activate.
10. Quarantine cannot choose a replacement.
11. Rollback restores only an exact prior authorized digest.
12. Every state-changing rollout action is receipt-bound.
13. Factory OS cannot infer authority from credentials, command transport or artifact possession.
14. VAIG, REHT, RACS and Core remain mandatory for consequence-bearing execution.

## Implementation ownership

Issue #32 owns:

- promotion request intake and validation;
- rollout state machine;
- behavior risk classification;
- separation-of-duties checks;
- bounded missions for repository and deployment changes;
- shadow, canary, activation, quarantine and rollback operations;
- receipt contracts and no-bypass tests.

Research Factory issue `nsolland/research-factory#124` owns the learning and evaluation half.

The canonical cross-repository build order lives in:

`nsolland/Index/projects/valo-as/research/AGENT_BEHAVIOR_GOVERNED_RECURSIVE_MULTI_AGENT_LEARNING_ADOPTION_AND_BUILD_ORDER_2026-08-04.md`

## Non-goals

- autonomous self-modification;
- direct model-weight updates;
- treating Agent Behavior as policy;
- activating behavior from Research Factory;
- allowing agent consensus to create authority;
- replacing REHT, RACS, Core or VERITAS.