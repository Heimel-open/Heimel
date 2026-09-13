# Representation is not the person

Date: 2026-08-17  
Status: canonical clarification / research architecture correction  
Epistemic status: `hypothesis` / `architectural_definition` where explicitly stated  
Scope: digital twins, Framleis, Digital DNA, personal AI, authority

## Correction

The digital representation is never the person it represents.

Increasing fidelity does not change that category. A representation may become extremely rich, predictive, persistent and useful while remaining a representation.

Working formulation:

> **When is the clone still you? Never.**

This is used here as an architectural boundary, not as a metaphysical proof.

The correction removes an unnecessary premise from the digital-twin problem. Framleis does not need to establish that a digital twin is "still the person". It can instead address a narrower and operationally testable question:

> **Is the current representation a trustworthy continuation of the earlier representation?**

## Canonical separation

```text
prediction      != decision
representation  != person
continuity      != identity
inference       != consent
knowledge       != authority
similarity      != standing
```

And:

```text
Model predicts.
Twin represents.
Framleis preserves continuity and integrity of the representation.
REHT authorizes intervention.
```

The four functions remain separate.

## 1. What a twin is

A digital twin is a maintained representation of a principal or system. For a person it may contain, subject to scope and provenance:

- observations and evidence;
- declared preferences and goals;
- decision history and reasons;
- relationships and constraints;
- resources and commitments;
- inferred patterns;
- uncertainty and unresolved state;
- historical state and superseded state.

The representation may be highly useful without being the represented person.

A model may predict the person from the representation. That prediction remains a prediction.

## 2. What Framleis now needs to prove

For digital-twin use, Framleis should not claim to prove persistence of personal identity.

Its operational object is the representation lineage.

Framleis can evaluate whether a transition preserves required properties such as:

- source provenance;
- state integrity;
- declared invariants of the representation;
- authorized amendments to the representation;
- lineage between previous and current state;
- explicit uncertainty and contradiction;
- bounded scope and purpose;
- detection of poisoning, silent rewrite, fork or cumulative drift.

A state can change substantially while remaining a trustworthy continuation of the maintained representation.

## 3. Digital DNA as verifiable lineage

Digital DNA should be interpreted operationally as a verifiable lineage for how the representation evolved.

Conceptually:

```text
R0 --t1--> R1 --t2--> R2 --t3--> R3
```

where each transition can carry:

```text
source evidence
provenance
transformation
amendment basis
integrity binding
supersession / contradiction state
continuity result
```

The Digital DNA grammar can therefore be read as:

```text
S = representation state space
T = admissible representation transformations
~ = representation-equivalence relation for the declared continuity contract
I = representation invariants / structures that must be preserved
C = continuity-collapse conditions
```

This does not establish metaphysical identity of the person. It establishes accountable continuity of the representation.

## 4. Legitimate novelty remains possible

The correction does not turn Framleis into a freeze mechanism.

A later representation may contain a genuinely new judgment, preference, commitment or architecture that could not have been predicted from the earlier representation.

That novelty may still be a legitimate representation update if its lineage, provenance, amendment basis and required invariants remain intact.

Therefore:

```text
low predictability != broken representation continuity
```

Framleis should distinguish surprise from lineage rupture.

## 5. Fidelity does not create authority

A representation can:

- know a great deal about the principal;
- predict what the principal would probably choose;
- recommend a choice;
- simulate second- and third-order consequences;
- preserve historical wishes and decisions with high fidelity.

None of these creates action authority.

Authority must come separately from an authoritative source: for example the principal, a legitimate delegation chain, a valid mandate, law or another recognized authority mechanism.

At consequence time, the proper runtime authority boundary must evaluate that authority independently of model fidelity.

Canonical rule:

> **Fidelity can increase evidential value. It does not automatically increase authority.**

## 6. Incapacity / dementia example

A rich historical representation may become valuable evidence if the principal later loses decision capacity.

It may preserve prior wishes, explicit decisions, values, risk preferences and reasons better than ordinary memory or scattered records.

But the representation does not thereby become the principal and does not automatically gain the right to decide on the principal's behalf.

Any right to act must come from a separate legitimate basis, such as a prior mandate, power of attorney, legal rule, guardian or other recognized authority chain.

The representation can inform that authority holder. It does not replace the authority holder merely by being accurate.

## 7. Consequence for bounded self-ensembles

Multiple specialized "Njål" projections are therefore not multiple Njåls and not fragments of Njål.

They are bounded reasoning models over one maintained representation of the principal.

```text
principal != canonical representation != specialized projection
```

An architecture projection, commercial projection, risk projection or synthetic-subconscious process may produce candidates and counterfactuals. None becomes the person; none owns the canonical representation; none gains authority from agreement or confidence.

This makes the ensemble safer to optimize: the system optimizes representations, reasoning strategies and decision support, not the person as an ontological object.

## 8. Security consequence

The refined failure classes are:

```text
model manipulation      -> bad prediction
representation poisoning -> bad represented state
lineage corruption       -> broken representation continuity
mandate hijack           -> illegitimate authority
```

These controls must remain separate.

## 9. Architectural flow

```text
principal / authoritative sources
        |
        v
observations + evidence
        |
        v
canonical twin / representation
        |
        +--> replaceable predictive models
        +--> bounded specialist projections
        +--> background / synthetic-subconscious reasoning
        |
        v
candidate prediction / recommendation / representation mutation / action
        |
        +--> Framleis: continuity, provenance and integrity for representation change
        |
        +--> separate authority source / delegation / mandate
        |
        v
REHT: consequence-time authorization
        |
        v
external consequence
```

No path from prediction, representation, continuity, optimization or consensus directly creates authority.

## 10. Moat consequence

For personal AI, the durable value need not be that an AI "becomes you".

A stronger and more defensible proposition is:

> **A high-fidelity governed representation of the principal, controlled by the principal, portable across models, provenance-preserving, continuity-verifiable, and strictly separated from the authority to act.**

The representation can become richer without claiming personhood.

## Non-claims

This note does not claim to resolve metaphysical personal identity.

It does not claim that a digital representation can never have legal status under any future legal system.

It does not define REHT runtime semantics.

It does not claim that representation continuity is equivalent to human psychological continuity.

It narrows the architecture so those claims are unnecessary.

## Canonical summary

```text
The person is the principal.
The twin is a representation.
The model predicts from the representation.
Framleis protects the representation's lineage, continuity and integrity.
Authority to act remains separately grounded.
```

Short form:

> **Representation is not person. Continuity is not identity. Knowledge is not authority.**
