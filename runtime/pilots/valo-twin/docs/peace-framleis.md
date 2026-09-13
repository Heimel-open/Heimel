# PEACE FRAMLEIS — Canonical Term Lock

Date: 2026-08-19
Status: CANONICAL / DO NOT TRANSLATE

## Normative lock

**Framleis** is the normative PEACE term.

> **Framleis must not be translated or replaced.**

`continuity`, `persistence`, `trajectory`, `becoming`, `persistent state`, and `identity through transformation` are partial English descriptions. None is equivalent to **Framleis**.

The term is intentionally retained in Nynorsk. Readers should learn the term rather than forcing the concept into a weaker English substitute.

## Meaning

Framleis names what remains through change without requiring stasis or sameness of state.

It emerged from the tension between:

```text
ER    — what is
BLIR  — what changes / becomes
FRAMLEIS — what continues through the becoming
```

The actor is not a frozen state snapshot. State, memory, relationships, preferences, commitments, standing, obligations and evidence may all change. Cognition providers and compute substrates may also change.

Yet the actor can be **Framleis**.

A compact PEACE formulation is:

> **Intelligence reasons. State changes. The actor is Framleis.**

## Architectural consequence

PEACE therefore does not equate an actor with:

- a model;
- a checkpoint;
- a context window;
- a memory store;
- one state snapshot;
- one compute substrate;
- one worker.

The governed system instead preserves an attributable, admissible path of transformation across state changes while replaceable intelligence operates on it.

```text
current governed state
  -> replaceable cognition
  -> candidate transition
  -> standing / authority / admissibility
  -> consequence
  -> receipt
  -> admitted next state
  -> ...
```

Framleis is the persistence through that transformation, not the immobility of any one element.

## Relationship to existing implementation names

The existing `peaceContinuityKernel`, `continuityRoot`, and related API names predate this canonical terminology lock. They remain implementation names for compatibility in the current demonstrator.

They MUST NOT be interpreted as defining the full normative concept. `continuityRoot` is a technical projection used by the demo; **Framleis** is the broader concept.

Future API naming may introduce `framleis` directly, but no compatibility refactor is required merely to establish the semantic lock.

## TOFOO -> PEACE convergence

Framleis was already established in TOFOO through the earlier exploration of `er`, `blir`, persistence and transformation, including the decision that the Nynorsk term should not be translated away.

PEACE reached the same requirement independently from system architecture:

```text
govern the workspace, not the worker
  -> worker becomes replaceable
  -> intelligence becomes replaceable
  -> separate what persists from intelligence
  -> state is dynamic rather than frozen
  -> continuity alone is too narrow
  -> Framleis
```

This is conceptual convergence, not a retroactive rename.

TOFOO explored what Framleis means. PEACE independently exposed why such a primitive is architecturally necessary.

## Canonical rule

When PEACE refers to the evolving persistence of an actor through governed transformation, the normative term is:

> **Framleis**

Do not replace it with `continuity`, `persistence`, `trajectory`, `becoming`, or an English compound. Those terms may explain aspects of Framleis, but they do not rename it.
