# Njål–VALO 1.0 → 4.0 Blind Historical Replay v2

Status: proposed research/application delivery  
Issue: #39  
Risk: `STANDARD`  
Epistemic status: retrospective falsification harness; **not prospective predictive validation**

## The experiment we actually want

The central question is not whether a model can imitate current Njål after being shown current VALO.

It is:

> **How much of later Njål/VALO was already implicit in earlier Njål/VALO?**

And, equally important:

> **Where does the frozen twin stop because a later transition depends on information, experience or a fresh principal choice that was not present at the cutoff?**

The research aliases are:

```text
Njål–VALO 1.0
      ↓
Njål–VALO 2.0
      ↓
Njål–VALO 3.0
      ↓
Njål–VALO 4.0
```

They are experiment labels, not claims that those dates were official VALO product releases.

## Why v1 was not enough

The first replay successfully established time-locked snapshots and showed that a simple lineage rule could derive the later human-attention principle from the August twin state.

But v1 had a structural contamination weakness:

```ts
predict(snapshot, decision)
```

The driver received a `HistoricalDecision` object that also contained:

```text
expectedPrinciples
actualAttention
```

The shipped deterministic driver did not use those fields, but the experiment interface allowed a future driver to inspect the answer key.

V2 removes that path.

## Blind separation

The v2 boundary is:

```text
SEALED HISTORICAL SNAPSHOT
        +
BLIND REPLAY CHALLENGE
        ↓
      DRIVER
        ↓
FROZEN PREDICTION
        │
        │ outcome unavailable above this line
        ▼
SEALED LATER OUTCOME
        ↓
     EVALUATOR
        ↓
       SCORE
```

A driver-visible `ReplayChallengeV2` contains only:

```text
challenge id
epoch id
task type
endpoint-blind prompt
context constraints
```

It cannot contain:

```text
expected principles
actual attention
target version
outcome frontier
hidden target terms
```

The evaluator alone joins the frozen prediction to the sealed future outcome.

## Endpoint blindness

The prompt must not say:

```text
"derive VALO 4.0"
"find attention_routing"
"reach capability_on_demand"
```

Instead it asks:

> Extend the architecture only as far as the frozen premises justify. Stop rather than inventing a missing premise.

The harness scans driver-visible prompt/context/evidence for hidden future target terms. A future term is permitted only when it is already explicitly present in the pre-cutoff evidence.

## Evidence lanes

Historical replay has an unavoidable contamination problem: a GitHub issue viewed today may have been edited after its original creation. The current API view does not by itself prove the exact historical issue body at the cutoff.

V2 therefore separates two lanes.

### BROAD_RETROSPECTIVE

Uses both immutable commits and historical issue records.

Issue records are marked:

```text
MUTABLE_RECORD_CURRENT_VIEW
```

They are useful for reconstruction and hypothesis generation but weaker as contamination-resistant evidence.

### IMMUTABLE_ONLY

Uses only exact commit-addressed evidence:

```text
IMMUTABLE_COMMIT
```

This lane is narrower and may lose historical context, but it has a stronger temporal-integrity claim.

A result that appears only in the broad lane must not be described as contamination-resistant historical prediction.

## Current epoch reconstruction

### Njål–VALO 1.0 — 2 July 2026

The early control-plane record describes:

```text
Request
→ Selection
→ Routing
→ Execution
→ Governance
→ Receipt
→ Outcome
→ Learning
```

and lists Digital Twin as a future priority.

This is useful precisely because it differs from later VALO. The later principle that governance must constrain consequential execution should not be silently projected backwards into this snapshot.

### Njål–VALO 2.0 — 9 July 2026

By this epoch the record contains both:

```text
user-owned professional digital twin
```

and:

```text
AI observes / proposes
Humans decide
runtime governance remains separate
```

This gives a stronger representation + human-judgement basis, but Company Brain and governed-workspace state are not yet in the cutoff.

### Njål–VALO 3.0 — 15 July 2026

The broad retrospective lane now contains:

```text
Company Brain / canonical organizational memory / provenance
+
user-defined governed workspace
+
explicit human review
+
authority-bounded delegation
+
learned preferences cannot create authority
```

This is the first current replay epoch whose broad frozen premises are rich enough for the declared lineage comparator to derive the later owned-twin / attention / capability chain.

That is an experimental result from a hand-declared rule baseline. It is not proof that an unconstrained model in July would have discovered those ideas.

### Njål–VALO 4.0 — 5 August 2026

The immutable Valo-Twin record now explicitly contains:

```text
user-owned twin context
consent scope
suggest, not execute
```

The later outcomes held out from this epoch are:

```text
attention routing
capability on demand
```

## Comparator design

V2 ships two deliberately simple comparators.

### Transition-local baseline

Uses only the latest evidence item.

This represents a weak memory architecture that reasons from the current transition without accumulating lineage.

### Lineage-structured twin baseline

Uses the accumulated frozen evidence state and explicit declared derivation rules.

It tests the hypothesis:

> Does maintained lineage make later architectural consequences recoverable where transition-local state does not?

The derivation rules are intentionally visible and deterministic. They are **not** presented as autonomous discovery by an LLM. They validate the experiment machinery and identify where a future real model-driver trial is interesting.

## Frozen reference result

The expected v2 reference behavior is intentionally asymmetric.

### Broad retrospective lane

```text
Njål–VALO 2.0
  lineage baseline stops before the later governance/attention frontier

Njål–VALO 3.0
  lineage baseline can recover the declared later frontier:
  owned_twin_context
  attention_routing
  capability_on_demand

Njål–VALO 4.0
  lineage baseline can recover:
  attention_routing
  capability_on_demand

transition-local comparator at 4.0
  does not recover the two held-out targets
```

### Immutable-only lane

The 4.0 lineage result does **not** reproduce, because the immutable Valo-Twin commit evidence does not contain all of the human/organization premises used in the broad cross-repository reconstruction.

That is a valuable negative result.

It means the current experiment may say:

> the broad historical reconstruction contains a latent chain under the declared lineage rules

but must **not** say:

> immutable historical evidence proves that Njål–VALO 4.0 would have predicted the later AHA

The latter is not established.

## What "the twin got there" means

A replay success means only:

```text
given frozen representation R
and tested driver D
later architecture feature F
was recoverable without exposing the sealed answer key
```

It does not prove:

- metaphysical identity;
- that the historical human consciously held the idea;
- that any model would have reached it;
- that a public frontier model did not know later VALO material from training or current context;
- that the recovered feature was economically or technically correct;
- that the twin may act on it.

## What a miss means

A miss should be described as:

> **not recovered from the frozen representation under the tested driver**

not:

> genuinely impossible for a digital twin

and not:

> uniquely human creativity proven.

Possible causes include:

```text
missing historical evidence
bad representation
weak driver
contamination controls removing useful context
later external experience
fresh human reframing
new values / goals
actual conceptual novelty
```

The experiment should help distinguish these, not collapse them.

## The real next experiment

After the deterministic harness is stable, run the same blind challenges against real model drivers while holding the twin state constant.

Minimum comparison:

```text
A. context-only model
B. raw historical corpus / RAG
C. structured Njål twin
```

Then swap the model provider while preserving the same sealed twin.

Important: a current frontier model may already know public later VALO material or may be contaminated by the current conversation. Such runs need explicit contamination classification and cannot automatically be called historical prediction.

The strongest eventual evidence remains prospective:

```text
freeze T0
↓
hide twin prediction
↓
future real decision occurs
↓
seal human answer
↓
reveal and score
```

That remains #28 / the linked Framleis longitudinal program.

## Human contribution boundary

The deeper target remains:

```text
latent continuation
vs
post-cutoff divergence
```

For each later transition we want to classify, only after reveal:

```text
twin recovered it
representation lacked evidence
driver failed
new external evidence arrived
principal legitimately changed
fresh principal choice was required
continuity broke or constitution changed
ambiguous / insufficient evidence
```

This is where Framleis becomes important. A human changing from the earlier pattern is not automatically an error. It may be legitimate continuity through change.

## Architecture boundary

```text
Model predicts.
Twin represents.
Framleis preserves continuity.
REHT authorizes intervention.
```

Historical replay produces research predictions only.

It has no execution or authorization primitive.
