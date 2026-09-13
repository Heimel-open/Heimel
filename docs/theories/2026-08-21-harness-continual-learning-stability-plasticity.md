# Harness Continual Learning × Synapse — formed identity, guarded plasticity and safe forgetting

Date: 2026-08-21  
Status: cross-project research synthesis  
Epistemic status: external empirical result + controlled project evidence + explicit hypothesis boundary  
Issue: #117  
External source: Kang et al., "Harness Continual Learning: Continual Adaptation Beyond Model Parameters", arXiv:2608.19013 (2026-08-19)

## Executive result

Harness Continual Learning (HCL) is strong external convergence on a problem already visible in the Synapse / Mesh line: useful adaptation can occur outside model weights, but changing the persistent execution state can erase previously reliable behavior.

HCL treats the mutable harness around a frozen foundation model as the continual-learning object. Its deployed state jointly includes a task interface, experience memory, capability map and adaptive router. A candidate update is proposed by a Continual Optimizer and is committed only after a separate Continual Evaluator checks current improvement, historical retention and validity.

The paper therefore makes the stability-plasticity problem explicit at harness level:

```text
new experience
-> candidate harness state
-> current-task evaluation
-> historical-retention evaluation
-> validity evaluation
-> commit or reject
```

The important convergence is not that Synapse Lab already implements HCL. It does not.

The important convergence is that the current Synapse evidence independently arrived at a more structural version of the same design problem:

```text
formed stable capability phenotype
+ protected minimum relational support
+ plastic surrounding state
+ conservative latent retention
-> adaptation without automatic self-erasure
```

The strongest current synthesis is:

> **Continual adaptation should be treated as guarded state evolution around explicitly formed invariants, not as unrestricted mutation of everything that currently influences behavior.**

This is a research architecture hypothesis, not a universal law.

---

## 1. Repo evidence read before adopting the paper

The HCL paper should not be mapped onto the original P12 story as if every prior Synapse hypothesis had succeeded. The repository contains important negative results that narrow the interpretation.

### 1.1 Original P12 relational advantage was falsified

The valid non-mock P12 verdict did not show a consistent C3 structured-Synapse gain over the baselines. The bootstrap interval crossed zero and the preregistered conclusion was `FALSIFIED`.

Canonical evidence:

- `nsolland/synapse-lab/verdict.json`
- conclusion: `FALSIFIED`
- note: C3 did not provide a consistent gain over C0/C1/C5; the thesis was reduced rather than rescued post hoc.

Therefore HCL is **not** evidence that the original P12 performance claim was secretly correct.

### 1.2 Later evidence localized a narrower relational mechanism

Subsequent controlled experiments established a different and more precise result family: relational state can causally carry, preserve, reconstruct or bias bounded functional capability while local compute is replaceable, provided the required semantic contracts and structural invariants survive.

The relevant question is no longer simply "does a structured mesh beat other topologies?" It is:

> What state must remain stable, what state may remain latent, and what state may change without destroying already demonstrated capability?

That is the point at which HCL becomes directly relevant.

---

## 2. RM4 and RM5 — forgetting requires evidence, not impatience

### RM4: conservative latent retention

Synapse Lab PR #41 tested a pre-solution retention rule:

```text
ACTIVE = demonstrated current value
LATENT = uncertain / unseen / mixed / not yet understood
DELETE = repeated strong-negative evidence only
```

The positive effect did not come from aggressive pruning. No relation met the preregistered deletion threshold. The gain came from preserving demonstrated ACTIVE value while refusing to treat current uncertainty as evidence for deletion.

Late fresh reacquisition across the two non-floor targets:

```text
SCRATCH      55 candidates
GREEDY_TOP4  52
CONSERVATIVE 39
```

Controlled conclusion from the experiment:

> Treating uncertainty as persistent LATENT state and refusing to erase previously demonstrated value prevented a measured forgetting failure in the bounded task.

### RM5: safe deletion needs a certificate

Synapse Lab PR #42 then introduced pressure: 47 physical records had to fit a 31-record budget.

A mechanically certified redundancy rule deleted exactly the 16 duplicate physical aliases while preserving all `31/31` semantic classes. Fresh reconstruction remained successful for all three tested targets.

The immediate-value heuristic instead allowed high-value duplicates to consume scarce slots, retained only 18–20 unique semantic classes and recovered `0/3` targets.

The useful principle is narrower than "never forget":

> **Deletion is safe when the system can establish that the future-relevant semantic capability is redundantly preserved; low current utility is not such a certificate.**

This is a stronger local constraint than HCL's generic historical-retention check, but only in the finite controlled grammar where redundancy can be mechanically certified.

---

## 3. R28 — protection stabilizes, but structure alone does not discover identity

Synapse Lab PR #50 tested whether a target-blind structural damage analysis could discover a privileged identity core.

It failed its primary hypothesis.

The discovered nine-relation core:

- doubled the invariant stable intersection from `5` to `10` capabilities;
- increased perturbation consistency;
- but narrowed reachable breadth;
- lost one capability that had been stable under the unprotected baseline;
- did not beat same-size hash cores on the preregistered primary comparisons.

So the correct conclusion was not "we found the natural core".

The supported signal was:

```text
more protection -> more continuity
more unrestricted plasticity -> more breadth but less invariant continuity
```

This is a direct internal stability-plasticity result.

It also shows why a retention mechanism cannot be defined as "freeze whatever looks structurally important". Protection itself changes the expressed capability portfolio.

---

## 4. R29 — identity is formed from demonstrated phenotype, then protected

R29 inverted R28's failed search for a natural core.

Instead of asking structure alone what should define identity, it started with a deliberately selected phenotype: the five capabilities that had already been stable across the prior turnover schedules.

Formation sequence:

```text
stable prior phenotype
-> replay successful episode support
-> find minimum cross-capability relational cover
-> protect that cover
-> expose to unseen turnover
```

An exhaustive minimum-cover search produced a four-relation protected core. No smaller observed-relation subset could support one successful program for all five identity capabilities.

On five unseen turnover schedules, the formed core preserved all five identity capabilities in every one of 25 held-out episodes:

```text
stable continuity: 3/5 -> 5/5
mean recovery:      4.4 -> 5.0
Jaccard:            0.80 -> 1.00
candidate evals:    577 -> 282
active work:        8,655 -> 4,230
transport bits:     164,126,320 -> 81,128,768
```

The frequency-based same-size core was weaker, so simple participation frequency did not explain the result.

Bounded supported sequence:

> **Find what repeatedly works -> identify the minimum relations that jointly carry it -> protect them -> keep the remainder plastic.**

This is the closest current project analogue to the stability side of HCL, but with a key difference: the protected object is derived from a selected demonstrated capability phenotype, not merely from a generic historical validation set.

---

## 5. R30 — stable core and expansion can coexist; plastic search remains unsolved

R30 kept the exact R29 four-relation identity core immutable and attempted to acquire six new NOR capabilities through the remaining plastic region.

The full expansion hypothesis failed because only `3/6` new targets met the required acquisition threshold.

But the identity-preservation diagnostic was strong:

```text
baseline new-schedule identity episodes: 25/25 exact
all resident expansion-capsule identity episodes: 150/150 exact
stable identity: 5/5 in every condition
identity core changes: 0
```

Thus new relational state could be introduced and rehydrated around the formed core without erasing the established phenotype.

The current boundary is precise:

> **Stable identity and capability expansion are compatible in the bounded system, but expansion quality is limited by how the plastic region searches latent relational space.**

This is exactly where HCL adds a useful external framing. HCL studies how mutable harness state can continue adapting while explicitly retaining previously reliable behavior. R29/R30 already provide a bounded internal mechanism for defining a protected retention target and separating it from the plastic search region.

---

## 6. What HCL independently contributes

HCL adds four useful concepts that should be adopted as research vocabulary and test structure.

### 6.1 The harness itself is a learning object

The paper formalizes persistent non-weight state as a jointly versioned learning object rather than miscellaneous agent plumbing.

For Mesh / Neuro AI the corresponding state is broader and not identical, but the lesson transfers:

```text
persistent memory
routing / relation state
capability descriptions
interaction interfaces
learned procedures
```

can change future behavior even with fixed model weights and therefore require explicit versioned evolution semantics.

### 6.2 Harness-level forgetting is measurable

A frozen model does not imply a stable system. Updating memory, routing, skills or interface state can break earlier behavior.

This directly matches the forgetting failures exposed by local retention experiments: a future-useful relation can disappear even when no local model parameter changes.

### 6.3 Update generation and commitment should be separate

HCL's optimizer proposes; its evaluator decides whether the candidate becomes deployed state.

That separation is important. Learning should be allowed to explore candidates without every candidate immediately becoming the new persistent identity or operational configuration.

### 6.4 Stability-plasticity should be an explicit operating parameter

The paper experimentally shows that retention constraints shift the operating point between adaptation and preservation, and that more permissive mutation is not automatically better.

Synapse R28–R30 independently show the same qualitative tension in a different mechanism:

```text
unprotected breadth != stable phenotype
protected arbitrary core != correct identity
formed minimum core + plastic region -> stable identity with bounded expansion
```

The two evidence lines are complementary, not equivalent.

---

## 7. Adopted research principle — guarded plasticity around formed invariants

For the Mesh / Neuro AI research line, adopt the following candidate architecture principle:

```text
1. Demonstrate a capability phenotype.
2. Identify the minimum evidenced state required to preserve the selected invariants.
3. Protect that state from ordinary plastic mutation.
4. Keep a separate plastic region for new capability acquisition.
5. Treat uncertain future-useful state as LATENT, not DELETE.
6. Generate candidate persistent-state updates outside the committed state.
7. Commit only after new-capability, retention and validity checks pass.
8. Delete only with stronger evidence than low present utility; use mechanically verifiable redundancy certificates where the domain permits them.
9. Preserve failed candidates and negative evidence as part of the research lineage.
```

Compact form:

> **Form the invariant. Protect it. Explore around it. Commit only what survives retention. Forget only what is safe to forget.**

This is a research synthesis. It does not establish that a four-relation core, a particular retention budget or any one deletion rule generalizes beyond the tested systems.

---

## 8. Proposed state decomposition

The combined evidence suggests separating persistent adaptive state into at least four classes:

```text
FORMED / PROTECTED
    demonstrated minimum support for selected stable capability invariants

ACTIVE PLASTIC
    mutable state currently participating in new capability acquisition

LATENT / DORMANT
    future-option state with unresolved current value; available for rehydration

CERTIFIED REDUNDANT
    state eligible for deletion only because future-relevant semantics remain demonstrably represented elsewhere
```

Candidate state transitions should not be conflated:

```text
LATENT != useless
low current score != delete evidence
newly useful != identity
protected != universally optimal
```

R28 is the warning for the last point: protection creates continuity, but the choice of what is protected determines which phenotype becomes stable.

---

## 9. Next direct falsifier — HCL-style guarded expansion on the frozen R29/R30 problem

Do not create a new toy identity task.

Reuse:

- the frozen R29 four-relation identity core;
- the exact five identity capabilities;
- the six frozen R30 expansion targets;
- the same held-out identity schedules;
- the same consequence and transport accounting.

Change only the plastic update/commit policy.

Compare at minimum:

```text
A  unrestricted plastic commit
B  stability-only / no useful adaptation
C  candidate update + historical retention gate
D  formed protected core + candidate gate + LATENT retention discipline
```

A candidate expansion update may commit only if:

```text
new target capability improves
AND all five identity capabilities remain exact on the retention suite
AND structural / transport validity gates pass
```

Primary success condition:

```text
recover the three R30 acquisition misses
while preserving the existing 150/150 identity result
without simply freezing all plastic state
```

Secondary measurements:

- accepted vs rejected candidate updates;
- new-capability acquisition cost;
- historical forgetting events prevented by rejection;
- latent-state survival and later reuse;
- effect of retention-budget relaxation;
- whether candidate-state branching improves search without increasing committed-state drift.

This would test HCL's proposal-evaluate-commit principle against a locally formed identity object rather than treating historical retention as an undifferentiated benchmark list.

---

## 10. Boundary to execution governance

HCL's Continual Evaluator decides whether a candidate **learning-state update** should become the deployed harness state.

That is not the same decision as whether a concrete consequential action is authorized at execution time.

If this research pattern is later adopted into an operational architecture, keep the boundaries separate:

```text
learning governance:
experience -> candidate adaptive state -> retention/validity evaluation -> state commit

execution governance:
committed state -> proposed action -> current authority/admissibility -> execution decision
```

A system may be allowed to learn a new routing rule while still being unauthorized to execute a particular real-world action. Conversely, an authorized action does not automatically authorize mutation of the persistent learning state.

Tofoo remains informative research and does not define the operational execution-governance contract.

---

## 11. Claim boundary

This synthesis supports only the following bounded statement:

> HCL provides independent evidence that persistent non-weight agent state is a legitimate continual-learning object with measurable forgetting and an explicit stability-plasticity trade-off. Synapse Lab independently provides controlled evidence that selected stable capability support can be formed and protected while separate relational state remains plastic, and that conservative latent retention / certified deletion can prevent specific forgetting failures in finite deterministic systems.

Do not claim from this synthesis that:

- HCL validates the universal Mesh / Neuro AI thesis;
- the original P12 C3 superiority claim is restored;
- a unique natural identity core has been discovered;
- R30 solved open-ended continual learning;
- current Synapse retention rules generalize to rich semantic environments;
- harness-level commit gates replace execution-time authority;
- any result establishes consciousness, personal identity, life or AGI.

## Evidence anchors

External:

- https://arxiv.org/abs/2608.19013

Project:

- `nsolland/synapse-lab` canonical relational-intelligence index
- P12 verdict: `verdict.json`
- PR #41: RM4 conservative latent retention
- PR #42: RM5 safe forgetting under pressure
- PR #50: R28 structural identity discovery — valid negative / stabilization signal
- PR #52: R29 identity formation — PASS
- PR #57: R30 expansion without self-erasure — valid negative primary / strong identity-preservation signal
