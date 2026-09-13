# Relational Intelligence Observatory v0

Date: 2026-08-23  
Status: `FALSIFIABLE_RESEARCH_INSTRUMENT`  
Production adoption: **not authorized**

## Primary question

> **What would we observe if task-relevant intelligence were carried partly by higher-order, path-dependent relations rather than localized inside individual nodes?**

The objective is not to declare a system intelligent from complexity, coordination, persistence or surprise.

The objective is to build an instrument that can distinguish:

```text
ordinary node capability / ordinary complexity
```

from a narrower candidate signature:

```text
function that is unavailable from individual nodes or a current snapshot,
but becomes available when the correct relation and its history are preserved
```

Compact form:

> **Build the instrument that makes us less intelligence-blind.**

## Motivation and convergence

Current Tofoo/Synapse work already contains three relevant lines:

1. balanced XOR demonstrates a minimal case where task information is absent from each component alone but present jointly;
2. relational-seed / temporal-residue work asks whether history-bearing relation can become part of the functional substrate;
3. long-horizon AVO convergence treats persistent state, feedback and lineage as computational state rather than passive audit history.

A separate human–LLM case now adds a useful external research target: a long interaction can produce structures described as interaction-emergent, where prior interaction is reconstructed, formalized and fed back into later interaction. This is not evidence for the general hypothesis by itself, but it gives a natural long-horizon corpus on which the same observability logic can be tested.

## Candidate hypothesis

> **Intelligence may be a path-dependent property of persistent higher-order relations.**

This is deliberately stronger than `the network is the intelligence` and therefore carries stronger falsification obligations.

It predicts that some function should depend not only on node states and current connectivity, but on the specific history by which relational state was formed.

## Observable signature

A candidate relational-intelligence signature requires all of the following:

1. **Node insufficiency** — no individual node contains enough information/capability to explain the target function.
2. **Snapshot insufficiency** — the current joint state is materially weaker than the history-preserving relational representation.
3. **Relational gain** — preserving the correct higher-order relation materially improves prediction or task performance.
4. **History dependence** — shuffling or replacing lineage/history materially degrades the function while preserving relevant node marginals.
5. **Relation specificity** — rewiring otherwise equivalent components materially degrades the function.
6. **Replication** — the effect survives new seeds, instances or contexts.
7. **Transfer** — where claimed, the relational representation improves performance outside the originating episode.

A positive signature is **not proof of consciousness, agency, general intelligence, life or extraterrestrial origin**.

It is evidence for a narrower statement:

> some target-relevant function is carried by relational/historical structure that cannot be localized to the tested components alone.

## Core ablations

Every serious run should compare at least:

```text
NODE-A ONLY
NODE-B ONLY
CURRENT SNAPSHOT
FULL RELATION + HISTORY
HISTORY SHUFFLED
RELATION REWIRED
```

Where possible add:

```text
ENDPOINT-MATCHED / DIFFERENT LINEAGE
TIME-REVERSED HISTORY
IDENTITY-PRESERVING NODE SWAP
NEGATIVE-CONTROL RELATION
OUT-OF-DOMAIN TRANSFER
```

The key principle is simple:

> **If removing the proposed relational substrate does not remove the function, the relational claim fails.**

## v0 metrics

The reference probe reports:

```text
synergy_gain
    = full relational-history accuracy
      - best(node A, node B, current snapshot)

history_dependence
    = full relational-history accuracy
      - history-shuffled accuracy

relation_specificity
    = full relational-history accuracy
      - relation-rewired accuracy
```

Default candidate gate:

```text
full accuracy >= 0.95
synergy_gain >= 0.20
history_dependence >= 0.20
relation_specificity >= 0.20
```

These thresholds are instrument defaults, not universal scientific constants.

## First synthetic calibration

The v0 calibration corpus uses:

```text
y_t = XOR(A_t, B_t, A_(t-1), B_(t-1))
```

The corpus is balanced so that:

- A alone is insufficient;
- B alone is insufficient;
- current A+B is insufficient;
- correct current + previous relation determines the target;
- history shuffling destroys the learned mapping;
- relation rewiring destroys the learned mapping.

This synthetic result validates the detector plumbing only.

It must never be cited as evidence that natural or machine intelligence actually has this form.

## Next empirical target: long human–AI interaction

A natural next corpus is a long human–AI research interaction with preserved chronology.

The test is not whether the transcript sounds sophisticated.

The test is whether later capability contains measurable function that cannot be reconstructed from either participant or an endpoint snapshot alone.

Candidate protocol:

```text
1. freeze a long interaction trajectory
2. define blinded downstream research tasks
3. compare:
   A. base model + no relational history
   B. human-only artifacts / endpoint summary
   C. model + endpoint summary
   D. model + intact relational lineage
   E. model + shuffled lineage
   F. model + endpoint-matched synthetic lineage
4. score task-relevant reconstruction, transfer and correction behavior
5. test whether D materially exceeds A/B/C and whether E/F collapse the gain
```

Critical control:

> More tokens are not the variable of interest.

History must be compared against controls with similar information volume but altered relational ordering, provenance or lineage.

Otherwise the experiment measures context quantity, not path-dependent relation.

## Higher-order extension

For more than two nodes, pairwise edges may be insufficient.

Represent candidate state as:

```text
nodes
+ pairwise edges
+ hyperedges / group state
+ temporal lineage
+ retained negative evidence
```

Then ablate each layer independently.

A higher-order claim survives only if the function specifically depends on group structure that cannot be reduced to tested lower-order projections.

## Fermi / observational extension — hypothesis only

This instrument suggests a disciplined reformulation of one speculative question:

> If advanced intelligence were expressed primarily through distributed higher-order structure, what observables would distinguish it from ordinary natural complexity?

This is not a SETI claim and does not explain the Fermi paradox.

It changes the detection problem from:

```text
find a sender / message / artifact
```

to:

```text
find reproducible functional structure whose explanatory power appears only
at the relational / higher-order / historical level
```

The astronomy problem is much harder because interventions and rewiring controls are generally unavailable. Any future application would therefore require strong observational analogues, null models and natural experiments before an intelligence interpretation is admissible.

## Failure conditions

The hypothesis should be weakened or rejected for a target domain if:

- node-only models recover the same function;
- a current snapshot performs as well as intact history;
- shuffled history performs as well as true history;
- rewired relations preserve performance;
- gains disappear under information-volume-matched controls;
- the effect is explainable by leakage, identifiers or timestamp artifacts;
- the result fails replication;
- claimed transfer does not survive new contexts.

## Boundary to handlingsrett

Detecting relational or emergent capability does not authorize consequence-bearing action.

Keep the boundary explicit:

```text
observed / inferred capability
!=
legitimate authority
!=
handlingsrett
```

The observatory belongs in research and epistemic evaluation. Execution authorization remains a separate governed boundary.

## v0 implementation

Reference implementation:

`experiments/relational_intelligence/observatory.py`

Tests:

`tests/test_relational_intelligence_observatory.py`

The v0 implementation is intentionally zero-dependency and discrete. Its purpose is to lock the ablation logic before introducing learned models, embeddings, causal estimators or domain-specific complexity.

## Compact form

> **Do not ask only where the intelligence is. Remove the relation, scramble the history, rewire the structure, and see what capability disappears.**
