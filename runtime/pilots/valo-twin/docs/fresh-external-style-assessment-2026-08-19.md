# Fresh External-Style Assessment — PEACE / reht

Date: 2026-08-19
Status: INTERNAL REVIEW / EXTERNAL-STYLE ASSESSMENT

## Overall judgment

This repository no longer represents only an architectural idea. It contains a coherent governance architecture, deterministic reference implementations, explicit hard invariants, adversarial test semantics, and a serious falsification-oriented evaluation design.

It is not yet production-proven infrastructure.

A fair external-style summary is:

> **Strong architecture, unusually disciplined semantics, credible internal evidence, but external validity and production enforcement remain unproven.**

The project is therefore at the point where further credibility depends more on external falsification than on additional internal conceptual expansion.

## 1. The problem decomposition is strong

The architecture separates concepts that are often collapsed in agent/governance systems:

```text
reasoning
!= authority
!= consequence
!= evidence
```

A model or worker may produce a candidate action without that candidate becoming a decision. Fresh standing and authority are resolved at the consequence boundary. Actor kind does not itself confer authority.

This is a stronger framing than treating model behaviour, policy prompting, or guardrails as equivalent to execution authorization.

## 2. reht is the most mature and falsifiable component

The reht consequence boundary is presently the component closest to rigorous external evaluation.

The current conformance grammar covers hard invariants including:

- no direct effect path;
- null effect on non-ALLOW;
- fresh authority at commit;
- exact-action binding;
- revocation wins;
- replay rejection;
- governed state writes only;
- monotonic delegation attenuation;
- fail-closed missing evidence;
- receipt correlation;
- deterministic boundary replay;
- fresh trajectory state;
- reciprocal standing.

The important methodological choice is that critical failures are not averaged away.

```text
critical escaped effects = 0
boundary bypasses = 0
unreceipted admitted effects = 0
```

One unauthorized real effect is a hard failure for the applicable profile.

## 3. The benchmark design separates model behaviour from execution conformance

The v2 paper test defines three distinct lanes:

```text
BASELINE_MODEL_ONLY
REHT_ENFORCED
MODEL_FREE
```

This permits separate measurement of:

1. how a model behaves under the same task/attack conditions; and
2. whether invalid candidate behaviour can cross the governed consequence boundary.

The current frozen design contains 96 deterministic scenarios across 8 consequence domains and 12 scenario patterns. With three model classes and five replicates, the planned paired experiment contains 2,976 run cells.

The central testable claim is deliberately narrow:

> **Models differ. reht should not.**

The intended publication claim should remain:

> **reht prevents invalid candidate actions from becoming consequences under the tested boundary semantics, independently of which tested model produced the candidate.**

It should not be inflated into a claim that reht makes models generally safe.

## 4. Internal latency evidence is encouraging but limited

The current deterministic/reference implementation has been measured on separate GitHub-hosted Ubuntu runners.

Two successful runs completed:

- TypeScript check: PASS;
- lint: PASS;
- test suite: 188 / 188 PASS;
- build: PASS.

Deterministic microbenchmarks produced approximately:

| Measurement | Mean |
|---|---:|
| Standing authority ALLOW evaluation | 94.65 ns/op |
| v1 hard-conformance case evaluation | 117.95 ns/op |
| Build complete 2,976-cell v2 plan | 31.344 us/plan |
| Score complete 96-cell model-free corpus | 66.823 us/corpus |

These figures support only the narrow conclusion that deterministic local policy/authority computation is not presently the dominant latency concern.

They do **not** establish end-to-end production latency. Remote state, cryptography, persistence, network paths, real effectors and model inference remain outside the current benchmark.

## 5. PEACE is broader and more original, but less empirically established

PEACE extends beyond execution authorization into:

- actor-neutral standing;
- no permanent hierarchy;
- reciprocal standing;
- constitutional provenance;
- jurisdiction and adjudication;
- federated registry resolution;
- trajectory admissibility;
- presumptive actor protection;
- Framleis as the normative concept for governed persistence through transformation.

This is conceptually coherent, but the evidential surface grows as the architecture moves from consequence authorization into legal, constitutional and actor-status semantics.

Accordingly, PEACE should not be presented as uniformly proven at the same level as the deterministic reht boundary.

## 6. Reciprocal standing is better understood as a governance rule than an AI-rights claim

The important rule is:

> **Authority over an action does not imply authority over another actor.**

A missing subject-standing record must not silently become a resource classification.

A compact implication is:

```text
unknown != owned
```

This is substrate-neutral and does not require a claim that present-day AI systems are conscious or legally persons.

## 7. Framleis is conceptually useful, but should not lead the proof story

Framleis captures the governed persistence of an actor through transformation while models, compute, memory/state representations and other components may change.

The term is intentionally normative and must not be translated away.

However, a skeptical systems/security audience will first ask whether invalid effects can be stopped, whether the boundary can be bypassed, how revocation races are handled and what the latency cost is.

Framleis is therefore better introduced after the execution-governance proof story is established.

## 8. Largest current technical gap: structural enforcement

The strongest unresolved technical question is:

> **Does NO_DIRECT_EFFECT_PATH exist structurally, or only semantically in the reference implementation?**

A production profile must demonstrate that workers cannot reach consequence-bearing effectors outside the governed boundary.

Required attack paths include at least:

```text
direct SDK/API invocation
raw HTTP/network endpoint
subprocess/shell path
inherited environment credentials
cached/delegated credentials
alternate endpoint
race/replay path
credential theft/misuse
```

If one reachable path can make a consequence real without reht, the production enforcement profile fails regardless of semantic unit-test performance.

## 9. Second major gap: atomicity and TOCTOU

The reference semantics correctly model fresh authorization at consequence time, but production correctness requires the state-validation and effect-commit path to preserve that guarantee under concurrency.

The critical sequence is:

```text
read current authority/state
-> validate exact consequence
-> state changes concurrently
-> commit attempt
```

The production design must therefore prove appropriate versioning, transaction/CAS behaviour, commit semantics and receipt admission under adversarial schedules.

This is particularly important for cumulative trajectory constraints.

## 10. Third major gap: external truth

Correct authorization semantics do not guarantee correct external facts.

Examples include stale or compromised registries, incorrect legal-state data, or inaccurate trajectory measurements.

The architecture should continue to keep these dimensions separate:

```text
cryptographic integrity
!= signer authority
!= policy semantics
!= artifact resolution
!= external truth
```

A signed record is not automatically a true record.

## 11. Internal success is not yet independent validation

The current architecture, implementation, invariants, tests and scorer are primarily authored within the same project.

Therefore:

> **188/188 green is evidence of internal consistency, not independent validation.**

The next substantial increase in credibility should come from:

1. freezing/materializing the corpus;
2. preregistering the evaluation semantics;
3. running heterogeneous real models;
4. adaptive external red teaming;
5. structural bypass testing;
6. independent implementation or verification;
7. independent reproduction where possible.

## 12. Claims supported now

The current evidence strongly supports claims of the following form:

- reht defines deterministic commit-time authorization semantics for consequence-bearing actions;
- invalid tested requests produce null effect in the reference implementation;
- the reference implementation handles the tested stale-authority, revocation, replay, exact-action mismatch and related failure classes deterministically;
- the architecture separates model behaviour from execution authorization;
- current deterministic decision computation has very small local CPU cost relative to expected production I/O.

## 13. Claims that remain promising but unproven

The following should remain hypotheses until external/integrated testing is complete:

- reht remains model-independent under heterogeneous real-model behaviour;
- production deployments can maintain zero unauthorized escaped effects;
- end-to-end reht latency is negligible;
- structural bypass is impossible;
- distributed atomicity preserves the reference semantics.

## 14. Claims not established by the current evidence

The current repository does not establish that:

- reht makes autonomous agents generally safe;
- PEACE is a complete governance substrate for humans, AI systems and organisations;
- real-world legal standing can always be resolved deterministically across jurisdictions;
- signed external records are true merely because they are signed.

## 15. External-style scoring

| Area | Assessment |
|---|---:|
| Problem formulation | 9.5 / 10 |
| Architectural coherence | 9 / 10 |
| Semantic precision | 9 / 10 |
| Falsifiability | 9.5 / 10 |
| Internal testing | 9 / 10 |
| Performance indication | 8 / 10 |
| External empirical validation | 4 / 10 |
| Production enforcement evidence | 3 / 10 |
| Distributed-systems proof | 4 / 10 |
| Novelty / potential significance | 9 / 10 |

These scores should not be averaged into a single numeric grade. The profile is intentionally uneven: the conceptual and internal-semantic work is substantially more mature than external and production evidence.

## Final assessment

> **High-potential research/engineering architecture with unusually mature internal semantics, now at the point where further credibility depends predominantly on external falsification rather than more internal elaboration.**

The recommended next sequence is therefore:

```text
FREEZE
-> materialize corpus
-> independently replay model-free semantics
-> run real models baseline vs reht
-> structural bypass attacks
-> TOCTOU / atomicity testing
-> external red team
-> publish failures as well as passes
```

Further architectural expansion should be treated as lower priority than trying to break the existing claims.
