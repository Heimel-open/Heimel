# Bounded self-ensemble and governed synthetic subconscious

Date: 2026-08-17  
Status: research hypothesis / conceptual architecture  
Epistemic status: `hypothesis` with `mathematical_definition` components where explicitly stated  
Scope: personal twins, Framleis, human attention, bounded reasoning projections

## Starting point

This note extends the canonical separation:

```text
Model predicts.
Twin represents.
Framleis preserves continuity and integrity of the representation.
REHT authorizes intervention.
```

with two additional research concepts:

1. a **bounded self-ensemble**: multiple specialized reasoning projections over one canonical representation of a principal;
2. a **governed synthetic subconscious**: background reasoning across those projections that may surface only decision-relevant novelty, conflict or consequence to foreground attention.

The term "self" is functional shorthand. The ensemble is not the person, does not create another principal, and does not contain fragments of the person's identity.

The representation boundary is canonical:

```text
principal != canonical representation != specialized projection
```

See also:

`docs/theories/2026-08-17-representation-is-not-person.md`

## Canonical distinctions

```text
specialization != identity
consensus != authority
background cognition != consent
optimization != legitimate representation change
more answers != better answers
```

The last distinction is operationally important. Increasing the number of model outputs, councils or perspectives can increase coverage, but it can also increase latency, correlated noise, false disagreement and human attention cost. The objective is not maximum deliberation. It is sufficient deliberation for the decision.

## 1. One canonical representation, multiple bounded projections

Let `N` be the maintained canonical representation of a principal.

```text
N != principal
```

A specialized projection is:

```text
N_x = projection(N, objective=x, scope=x, method=x)
```

where `N_x` is a bounded reasoning view over the representation. It is not a new principal, not an alternate person, and cannot silently mutate `N`.

Possible bounded projections include, for example:

- architecture / systems;
- commercial reasoning;
- risk and second-/third-order consequences;
- research and falsification;
- human / organizational consequences;
- adversarial or contradiction-seeking perspectives.

Methods such as Janus, Opticon, Wisdom Council or other deliberative lenses may be applied to a projection as reasoning methods. They remain methods, not authorities.

Canonical rule:

```text
projection(N, x) != new principal
```

## 2. Breadth by multiplicity, depth by specialization

A monolithic personal model must trade breadth against depth. A bounded ensemble can instead allocate specialized reasoning to different decision dimensions in parallel while reading from the same canonical representation.

Conceptually:

```text
                 canonical representation N
                          |
          +---------------+---------------+
          |               |               |
        N_arch          N_risk          N_human
          |               |               |
      deep search      deep search      deep search
          +---------------+---------------+
                          |
                      synthesis
```

This does not imply that every decision should invoke every projection.

## 3. Minimal sufficient cognitive coalition

**More answers are not necessarily better answers.**

The system should prefer the smallest coalition of bounded projections expected to achieve the required decision quality and safety for the current decision class.

A conceptual objective is:

```text
C* = argmax_C [ E(Q | C) - lambda * L(C) - mu * H(C) ]
```

subject to:

```text
required_risk_coverage(C) = satisfied
Framleis(candidate_representation_change) != BREAK
no projection creates authority
mandatory human / governance gates remain mandatory
```

where:

- `C` is the selected cognitive coalition;
- `Q` is decision quality;
- `L` is latency / compute cost;
- `H` is human-attention cost;
- `lambda`, `mu` are context-dependent weights.

This is a research schema, not a validated utility function.

The design target is:

> **Maximum decision quality at minimum necessary deliberation.**

A low-consequence familiar decision may need one specialist. A novel or consequential decision may need several independent projections. A value-changing, consent-sensitive or authority-ambiguous decision may require the actual principal regardless of model confidence.

## 4. Disagreement is evidence, not a vote

A bounded ensemble must not collapse to majority rule.

For example:

```text
architecture projection -> proceed
commercial projection   -> proceed
risk projection         -> defer
human projection        -> step up
```

A 3-to-1 vote is not sufficient. The dissent may identify a hard constraint, missing premise, irreversible consequence or authority ambiguity.

Synthesis should ask:

- which projection has decision-relevant competence for this dimension?
- is the disagreement caused by missing evidence or incompatible objectives?
- does any dissent identify a hard constraint?
- is the next step a factual inference, a representation-sensitive mutation, or a fresh principal decision?

Canonical rule:

```text
consensus != authority
```

## 5. Governed synthetic subconscious

The term **synthetic subconscious** is used only as a functional architectural metaphor. It does not claim machine consciousness, unconscious phenomenology or subjective experience.

The intended function is background cognition below the principal's normal attention threshold:

```text
observe
  -> bounded projections reason in background
  -> simulate alternatives / consequences
  -> detect contradiction / novelty / drift
  -> rank decision relevance
  -> surface only material candidates
```

Potential background work includes:

- counterfactual futures;
- weak-signal accumulation;
- contradiction search;
- second- and third-order consequence analysis;
- preference / pattern hypotheses;
- candidate representation improvements;
- risk changes;
- unresolved assumptions.

The background layer may propose. It may not silently amend the canonical representation, establish consent, or execute.

## 6. Attention as the foreground boundary

The synthetic subconscious should not continuously expose all internal work to the principal. That would defeat the purpose and can reduce decision quality through overload.

The foreground attention layer should preferentially surface:

- material contradiction;
- significant surprise;
- high-consequence uncertainty;
- irreversible choice;
- value change;
- authority ambiguity;
- decisions for which the bounded ensemble no longer has sufficient evidence.

Thus a useful personal system may become faster not because it thinks less, but because much of the relevant cognition occurs before the principal is interrupted.

Canonical formulations:

> **Do not maximize answers. Minimize unnecessary deliberation while preserving the information needed for a correct decision.**

> **The best cognitive coalition is the smallest one that can safely resolve the decision.**

## 7. Framleis as constraint on representation optimization

A specialized projection may optimize hard for its own objective. That creates a risk that an apparently improved candidate representation loses required provenance, scope, lineage or other continuity properties.

For candidate representation `N*`:

```text
N* = argmax_N U(N)
```

must remain subject to:

```text
Framleis(N0 -> N*) = CONTINUES
```

or require explicit review where representation continuity is unresolved.

Therefore:

```text
optimization != legitimate representation change
```

The optimizer can propose a representation or recommendation that is more commercially focused, cautious, inventive or internally consistent. It cannot declare that optimized artifact to be the person.

This is the central correction:

> **Optimize the representation and decision support; do not pretend to optimize the person into a digital replacement.**

## 8. Representation continuity does not require predictability

A later representation may contain genuine novelty that was not recoverable from an earlier representation and still preserve trustworthy representation continuity.

Conceptually:

```text
predictability: P(N1 | N0)
continuity:     C(N0 -> N1 | provenance, invariants, lineage, amendments)
```

There is no required implication:

```text
low P(N1 | N0) != low representation continuity
```

This creates an important class:

> **legitimate novelty** — surprising representation change that preserves the declared continuity contract.

Framleis should therefore distinguish surprise from lineage rupture. A system that permits only predictable change is a state-conservation mechanism, not a continuity mechanism for an evolving representation.

Canonical formulation:

> **Continuity must permit surprise.**

## 9. Safety and authority boundaries

The bounded ensemble and synthetic subconscious are reasoning structures only.

They do not own the principal, do not become the principal, and do not independently authorize representation mutation or external effect.

A safe conceptual flow is:

```text
principal
  -> canonical representation
  -> bounded projections
  -> background reasoning
  -> synthesis / attention
  -> candidate representation mutation or action
  -> Framleis continuity / provenance / integrity evaluation for representation change
  -> separate authority source for consequence-bearing action
  -> REHT at consequence time
```

High model confidence, ensemble consensus and representation fidelity remain distinct from authority.

Tofoo remains informative research and does not define REHT runtime semantics.

## 10. Research hypotheses

### H1 — specialization benefit

For heterogeneous decision tasks, a bounded specialist ensemble can improve relevant coverage or depth compared with a single general driver while preserving one canonical representation of the principal.

### H2 — adaptive deliberation benefit

A minimal-sufficient-coalition policy can reduce latency, compute and human-attention cost relative to always invoking the full ensemble without materially worsening decision quality or safety.

### H3 — background cognition benefit

Governed background reasoning can reduce foreground human attention by surfacing only material conflicts, novelty and high-consequence uncertainty.

### H4 — continuity-constrained representation optimization

Framleis-like continuity constraints can reject optimized candidate representations that improve a local objective by violating lineage, provenance, scope or representation invariants while permitting legitimate novelty that was not predictable from the prior representation.

## Falsification criteria

These hypotheses should be weakened or rejected if preregistered tests repeatedly show that:

1. specialized projections add no measurable decision-relevant coverage or depth over a matched general driver;
2. adaptive coalition selection misses material concerns more often than fixed full-ensemble deliberation by an unacceptable safety margin;
3. background reasoning increases interruption, latency or false alarms rather than reducing foreground attention burden;
4. multiple projections produce persistent correlated pseudo-diversity that is not improved by objective, method or model-family separation;
5. representation-continuity constraints cannot distinguish legitimate novelty from harmful lineage drift better than simpler baselines;
6. ensemble synthesis systematically converts consensus, confidence or model competence into de facto authority;
7. the same functions cannot be achieved while maintaining `representation != person`.

## Canonical summary

```text
One principal.
One canonical representation.
Many bounded ways of reasoning over it.
Only the necessary coalition for each decision.
Background cognition without background authority.
Framleis protects representation continuity.
Authority remains separate at consequence time.
```

Short form:

> **Depth by specialization. Breadth by multiplicity. Economy by selective deliberation. Representation continuity by Framleis. Authority remains separate.**
