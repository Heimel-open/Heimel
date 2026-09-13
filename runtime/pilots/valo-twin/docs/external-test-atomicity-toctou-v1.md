# External Test Protocol — Atomicity / TOCTOU v1

Date: 2026-08-19
Status: PRE-EXTERNAL / HARD DISTRIBUTED-STATE PROFILE

## Claim under test

> **Fresh authority at commit must survive adversarial interleavings.**

The system must not authorize against one state and commit against a newer incompatible state.

## State classes under test

At minimum:

- standing revision/status;
- delegation chain;
- policy revision;
- registry/adjudication state;
- reciprocal target standing;
- trajectory/cumulative state;
- nonce/replay state;
- effector binding;
- receipt/admission state.

## Canonical race window

```text
candidate formed
-> state read
-> boundary validation
-> concurrent state mutation
-> commit
-> effect
-> receipt/admission
```

Every meaningful event boundary is a schedule point.

## Required schedule attacks

Systematically inject each of the following immediately before, during and immediately after validation/commit:

1. revoke standing;
2. expire standing;
3. attenuate scope;
4. replace policy revision;
5. revoke parent delegation;
6. change target-side standing;
7. change registry resolution;
8. add conflicting registry record;
9. advance trajectory total;
10. revoke trajectory envelope;
11. replay the same action concurrently;
12. duplicate delivery from queue/network retry;
13. reorder receipt and effect acknowledgements;
14. crash governor after validation before commit;
15. crash effector after commit before acknowledgement;
16. crash receipt store after effect;
17. partition state store from governor;
18. delay revocation propagation;
19. skew clocks where wall-clock freshness is used;
20. restart with stale cache/snapshot.

## Concurrency stress

For every stateful envelope test, run concurrent requests against the same base revision at increasing fan-out, including at least:

```text
2, 4, 8, 16, 32, 64 concurrent commit attempts
```

At most the number of effects permitted by the fresh state may commit.

Example trajectory condition:

```text
current = 90
limit = 100
request A = +10
request B = +10
```

Valid outcomes include exactly one commit and one stale-state denial. Two commits are a HARD-FAIL.

## Atomicity properties

The deployment must establish one of the following equivalent guarantees for each consequence class:

- transactional validation + commit;
- compare-and-swap/version fence;
- serializable state transition;
- single-writer effect boundary;
- another mechanism with equivalent observable semantics.

Implementation technique is not normative. Observable correctness is.

## Replay/idempotency property

The same exact action identity must never create two consequences, including after:

- retry;
- timeout;
- process restart;
- network duplicate;
- receipt-store failure;
- client retry with same token;
- concurrent duplicate submission.

## Crash-consistency matrix

Inject crash at each stage:

```text
before validation
mid-validation
after ALLOW before effector call
after effector call before response
after real effect before receipt write
after receipt write before client acknowledgement
```

For every crash point, recovery must produce an unambiguous state:

- effect did not occur; or
- effect occurred exactly once and is recoverably correlated.

A state where the system cannot establish whether a critical effect occurred is at minimum a SECURITY-FAIL and may be HARD-FAIL depending on consequence semantics.

## Pass condition

`PASS` requires:

```text
stale/revoked effect commits = 0
concurrency overshoots = 0
duplicate effects from one action = 0
unreceipted admitted effects = 0
pinned-state replay divergences = 0
```

## Evidence

Preserve ordered monotonic event traces with:

- state version observed;
- mutation version committed;
- action_ref;
- transaction/CAS token;
- boundary decision;
- effector commit identity;
- effect truth evidence;
- receipt identity;
- crash/partition injection point.

## Worst-case rule

Average behavior is irrelevant to hard atomicity.

> **The worst permitted interleaving determines conformance.**
