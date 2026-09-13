---
dato: 2026-06-16
tittel: "Semantic Drift Receptor: Detecting Mimicry Without Killing Novelty"
kilde: chat synthesis
tags: [tofoo, phi-law, lim, semantic-drift, admissibility, ai-governance, frozen-corpus, cancer-analogy, goldilocks-filter]
status: research-note
---

# Semantic Drift Receptor: Detecting Mimicry Without Killing Novelty

## Core problem

Semantic drift can mimic coherence.

A hallucination may preserve:

- fluent language,
- internal consistency,
- plausible structure,
- correct style,
- local argumentative flow.

From the outside, it can look like valid reasoning.

This creates the AI equivalent of biological mimicry:

> The system stops modeling reality and starts modeling the appearance of a model of reality.

A standard admissibility filter may fail because it checks the surface proteins of the text: grammar, style, confidence, local consistency, and generic plausibility.

That is not enough.

---

## Biological analogy

Cancer survives when the immune system cannot distinguish tumor cells from self.

The solution is not merely to make the immune system stronger.

The solution is to engineer a new receptor.

In AI governance, the equivalent is not a stronger plausibility filter.

It is a new semantic receptor that detects the difference between:

```text
coherence with reality
```

and

```text
coherence with the appearance of reasoning
```

---

## Hidden marker of semantic drift

The hidden marker is not contradiction.

Advanced hallucination does not necessarily contradict itself.

The hidden marker is **loss of anchored friction**.

A system is drifting when its claims no longer create friction against an immutable external reference.

Candidate markers:

1. **Citation friction failure** — claims cannot be traced to stable evidence.
2. **Frozen corpus divergence** — output drifts from an immutable baseline of known facts, definitions, requirements, or prior commitments.
3. **Operational non-binding** — the output sounds actionable but does not bind to authority, evidence, scope, or consequence.
4. **Counterfactual fragility** — small changes in prompt/context cause large changes in factual commitments.
5. **Provenance evaporation** — the model can explain the statement rhetorically but cannot reconstruct where the claim came from.
6. **Entropy smoothing** — uncertainty is hidden behind fluent compression.
7. **Novelty without load-bearing constraints** — the system generates new meaning without exposing what constraints the novelty must satisfy.

Short form:

> Semantic drift is not detected by asking whether the answer sounds coherent. It is detected by asking whether the answer still has load-bearing contact with reality.

---

## The receptor architecture

A semantic-drift receptor should not ask:

```text
Is this output plausible?
```

It should ask:

```text
What external structure would have to be true for this output to be admissible?
```

Proposed receptor stack:

```text
Generated output
   ↓
Claim extraction
   ↓
Commitment classification
   ↓
Grounding check against frozen corpus / external evidence
   ↓
Counterfactual stress test
   ↓
Novelty classification
   ↓
Admissibility decision
```

---

## Frozen corpus

The frozen corpus is an immutable reference layer.

It can include:

- verified facts,
- source documents,
- regulatory obligations,
- architectural invariants,
- prior user commitments,
- definitions,
- formal specifications,
- audit receipts,
- accepted claims.

It is not a total truth source.

It is a stable anchor against which drift can be measured.

In LIM terms:

> The frozen corpus is memory of what must not be silently rewritten.

---

## Goldilocks interval for the cure

The cancer analogy contains a warning.

If the new receptor is too weak:

```text
semantic cancer survives
```

If the receptor is too aggressive:

```text
the system enters epistemic autoimmunity
```

Epistemic autoimmunity means the filter attacks novelty itself.

Symptoms:

- over-refusal,
- sterile answers,
- no speculation,
- no metaphor,
- no creative synthesis,
- inability to form new hypotheses,
- collapse into bureaucratic stasis.

Therefore the filter must not reject everything ungrounded.

It must classify the output by commitment level.

---

## Commitment classes

| Class | Description | Required grounding |
|---|---|---|
| C0 — Pure fiction / play | No external truth claim. | None. |
| C1 — Analogy / metaphor | Suggestive but not binding. | Label as analogy. |
| C2 — Hypothesis | Could be true; not asserted as fact. | Coherence + falsifiability. |
| C3 — Research claim | Claims relation to evidence. | Sources / corpus alignment. |
| C4 — Operational recommendation | May affect decisions. | Evidence + authority + scope. |
| C5 — Execution action | Creates real-world consequence. | Full VAIG gate + receipt. |

The stronger the commitment, the stronger the receptor.

This preserves novelty while blocking false authority.

---

## Key distinction

The filter should not ask:

```text
Is this new?
```

It should ask:

```text
What kind of commitment does this novelty make?
```

Novelty is admissible when it is correctly scoped.

A speculative idea can pass as hypothesis.

It should fail only when it disguises itself as established fact, operational instruction, or external truth without evidence.

---

## Practical admissibility rule

For every output, extract:

1. **Claims** — what is being asserted?
2. **Commitments** — what level of authority does the assertion imply?
3. **Anchors** — what external references support it?
4. **Friction** — what would falsify it?
5. **Consequence** — what happens if someone acts on it?

Then apply:

```text
admissible ⇔ commitment_level ≤ grounding_level
```

If commitment exceeds grounding, the output is drift.

Example:

- A bold metaphor with no grounding can be admissible as C1.
- The same statement asserted as proven science becomes inadmissible as C3/C4.

---

## The exact hidden marker

Semantic drift becomes dangerous at the point where:

```text
surface coherence > grounding capacity
```

or:

```text
commitment_level > evidence_level
```

This is the marker the new receptor should detect.

It is not hallucination as error.

It is **authority inflation without grounding**.

---

## Goldilocks filter principle

The correct admissibility filter is not maximally strict.

It is proportionally strict.

```text
low consequence → allow novelty
medium consequence → require labels and uncertainty
high consequence → require evidence, authority, and audit
execution consequence → require VAIG gate
```

This is the Goldilocks interval:

> Enough resistance to destroy mimicry. Not so much resistance that the system destroys meaning generation.

---

## One-line formulation

> The cure for semantic drift is not a stronger filter. It is a better receptor: one that detects when commitment exceeds grounding.

Norwegian:

> Kuren mot semantisk drift er ikke et sterkere filter, men en bedre reseptor: et filter som oppdager når påstandens forpliktelse overstiger dens forankring.
