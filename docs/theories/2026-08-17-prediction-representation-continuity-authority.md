# Prediction, representation, continuity and authority

Date: 2026-08-17  
Status: canonical Tofoo synthesis / research hypothesis  
Epistemic status: `hypothesis` with `mathematical_definition` components where explicitly stated  
Scope: Digital DNA / Framleis / digital twins / persistent dynamic systems

## Canonical separation

```text
Model predicts.
Twin represents.
Framleis preserves continuity and integrity of the representation.
REHT authorizes intervention.
```

Canonical distinctions:

```text
prediction      != decision
representation  != person
continuity      != identity
inference       != consent
knowledge       != authority
similarity      != standing
```

The objects answer different questions and must not be collapsed into one AI system.

The digital representation is not the person it represents. Increasing fidelity, predictive accuracy or persistence does not change that category.

This clarification is developed in:

`docs/theories/2026-08-17-representation-is-not-person.md`

### 1. Prediction

A model estimates what a person or system may believe, prefer, decide or do under given conditions.

Prediction is probabilistic. It may be wrong, replaced, retrained, routed or compared with competing models.

A prediction does not become a decision merely because it is accurate. It does not become authoritative merely because it is highly confident.

### 2. Representation

A twin is the maintained representation of the principal or system: relevant state, history, relationships, goals, constraints, resources, evidence, uncertainty and derived state.

The twin is not the principal.

The twin is also not identical to the model that predicts from it.

This separation permits multiple models to operate against the same maintained twin state and permits models to be replaced without replacing the represented state.

A representation may become extremely rich and useful while remaining a representation.

### 3. Continuity

For digital-twin use, Framleis asks whether the current representation remains a trustworthy continuation of the earlier representation through change.

It does not need to prove that the representation is "still the person" or establish metaphysical personal identity.

The Digital DNA grammar is therefore operationalized as:

```text
S = representation state space
T = admissible representation transformation class
~ = representation-equivalence relation under the declared continuity contract
I = representation invariants / structures that must be preserved
C = continuity-collapse conditions
```

Continuity is not static sameness. A representation may change substantially while retaining accountable lineage, provenance and integrity.

Conversely, every local transition may look individually admissible while accumulated lineage leaves the intended representation class. This motivates lineage-level continuity testing in addition to transition-level checks.

Digital DNA is therefore best read operationally as a **verifiable lineage for how the representation evolved**, not as proof that a digital object is the person.

### 4. Authority

REHT answers a separate question at the consequence boundary: whether the proposed external effect is legitimately authorized here and now.

Authority must be grounded separately in an authoritative source: for example the principal, a legitimate delegation chain, a valid mandate, law or another recognized authority mechanism.

A representation may preserve strong evidence of what the principal previously wanted, decided or authorized. That can increase evidential value. It does not automatically make the representation an authority holder.

Continuity does not grant authority.

Similarity does not grant authority.

Prediction does not grant authority.

Representation does not grant authority.

Inference does not grant consent.

Tofoo remains informative research and does not define REHT runtime semantics.

## Architectural consequence

The digital twin should not be treated as a monolithic personal AI or as a digital person.

A minimal conceptual stack is:

```text
principal / authoritative sources
        |
        v
observations / evidence
        |
        v
Twin -- maintained representation
        |
        +--> replaceable predictive models
        +--> bounded specialist projections
        |
        v
prediction / recommendation / candidate mutation / candidate action
        |
        +--> Framleis / Digital DNA
        |     representation continuity, provenance and integrity
        |
        +--> separate authority source / delegation / mandate
        |
        v
REHT -- execution-time authority decision
        |
        v
external consequence
```

The model is a worker or driver. The twin is a maintained representation. Framleis governs continuity and integrity of that representation. REHT governs consequence-bearing authority.

## Security consequence

The separation exposes distinct failure classes that should not be conflated:

```text
model manipulation       -> bad prediction
representation poisoning -> bad represented state
lineage corruption       -> broken representation continuity
mandate hijack           -> illegitimate authority
```

A secure system therefore requires different controls for each layer.

A cryptographically authenticated model or account can still operate on a poisoned twin.

A perfectly continuous representation can still lack authority for a proposed action.

A highly accurate predictive model can still have zero authority.

## Model portability

If the separation holds operationally, model providers become replaceable with respect to the represented principal.

The principal can retain a governed canonical representation while allowing different models to read bounded projections, make predictions, propose updates or generate intents.

This yields the design rule:

```text
The model may learn about the principal.
The model does not become the principal.
```

And:

```text
The model may propose a representation mutation.
It may not silently redefine the continuity contract that judges that mutation.
```

## Bounded self-ensemble extension

One canonical representation may support multiple specialized bounded reasoning projections without creating multiple principals. Those projections may operate in parallel or in the background, but specialization remains distinct from identity, consensus remains distinct from authority, and more answers are not necessarily better answers.

The projections are models of the principal through bounded views of the representation; they are not fragments or alternate versions of the person.

The extension is developed in:

`docs/theories/2026-08-17-bounded-self-ensemble-synthetic-subconscious.md`

## Legitimate novelty

Representation continuity does not require perfect predictability.

A later representation may contain a genuinely new judgment, preference, commitment or architecture that could not have been recovered from the earlier representation.

That novelty may still be a legitimate update if provenance, amendment basis, lineage and required invariants remain intact.

```text
low predictability != broken representation continuity
```

Framleis should therefore distinguish surprise from lineage rupture.

## Incapacity example

A rich representation may preserve unusually good evidence of a principal's earlier wishes, values, decisions and reasons even if the principal later loses decision capacity.

That representation can be valuable evidence. It does not thereby become the principal or automatically acquire the right to decide on the principal's behalf.

Any such right must come from a separate legitimate authority basis such as a prior mandate, power of attorney, law, guardian or another recognized authority chain.

Fidelity can increase evidential value. It does not automatically increase authority.

## Generalization beyond persons

The same representation / continuity / authority separation may apply to other persistent dynamic systems provided their state space, admissible transformations, equivalence relation, invariants and collapse conditions can be declared and tested.

Candidate domains include:

```text
person
team
company
institution
community
city
infrastructure system
economic subsystem
```

This is a research generalization, not a claim that these systems are ontologically equivalent or that one universal model captures them all.

The hypothesis is narrower:

> Persistent systems can sometimes be represented by governed state, predicted by replaceable models, evaluated for continuity of the representation under declared transformations, and governed separately at intervention boundaries.

## Nested twins

A larger-system twin need not own the lower-level representations that contribute to it.

Example:

```text
person representation
   |
   +-- bounded projection --> team representation
                              |
                              +-- bounded projection --> company representation
```

Each level may have its own:

- state and provenance;
- representation-continuity contract;
- authority boundary;
- update cadence;
- permitted projections from lower or adjacent levels.

The person representation can remain controlled for the person's own purposes while the company representation receives only the state required for its legitimate purpose.

This avoids treating organizational membership as ownership of a digital representation of the person.

## Second- and third-order consequence modeling

Once representations exist at multiple levels, predictive models can simulate interactions across them.

For example:

```text
person leaves company
-> capability loss
-> relationship loss
-> decision latency change
-> customer confidence change
-> revenue / capital consequences
```

The predictive model may estimate these trajectories.

The company twin maintains the represented organizational state.

Framleis can test whether the maintained representation has crossed a declared regime or continuity boundary.

REHT or another legitimate intervention boundary remains required before a simulation is converted into real-world action.

Canonical rule:

```text
Prediction is not intervention authority.
```

## What this changes about "world models"

This synthesis does not require one monolithic model to own the representation of the world.

An alternative architecture is a mesh of scoped governed representations, each with its own state, provenance, continuity contract and authority boundary, while predictive models operate across bounded projections of those representations.

This is a conceptual alternative to equating a larger predictive model with a larger source of authority.

## Testable claims

The synthesis should be weakened or revised if any of the following repeatedly hold under preregistered tests:

1. Model replacement necessarily destroys useful representation continuity even when canonical twin state and lineage are preserved.
2. A maintained twin state provides no measurable advantage over direct model memory for portability, auditability or continuity detection.
3. Declared representation-continuity contracts cannot distinguish legitimate evolution from adversarial drift better than simpler baselines.
4. Nested representations cannot preserve useful local boundaries without producing inconsistent or unusable system state.
5. Separating prediction, representation continuity and authority adds no meaningful safety or governance benefit at consequence-bearing boundaries.
6. Treating the twin purely as a representation makes required personal-AI functions impossible unless the architecture collapses representation into personal identity.

Synthetic tests can expose implementation weaknesses but cannot prove metaphysical personal identity or validate the generalization across all domains.

## Canonical formulations

```text
Model predicts.
Twin represents.
Framleis preserves representation continuity.
REHT authorizes intervention.
```

Strict separation:

```text
Prediction is not decision.
Representation is not person.
Continuity is not identity.
Inference is not consent.
Knowledge is not authority.
```

And:

> **The person is the principal. The twin is a representation.**

This is the core synthesis.
