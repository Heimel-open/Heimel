# PEACE Continuity — Discovery Lineage

Date: 2026-08-18

This note preserves the provenance of the continuity and standing reductions in PEACE.

## Prior frame

Njål Solland established the preceding architectural frame through the VALO/PEACE work:

- govern the workspace, not the worker/model;
- the person or organisation is the persistent governed domain;
- intelligence, compute, routing and services are replaceable capabilities;
- worker output is a candidate, not a decision;
- authority is checked fresh at consequence time;
- revoked or invalid authority produces NULL EFFECT.

## Continuity reduction

The next reduction was proposed by OpenAI ChatGPT (GPT-5.6 Sol) during the working session on 2026-08-18:

> We have separated intelligence from authority. The next reduction is to separate continuity from intelligence.

This led to the formulation:

> The model thinks. The sovereign domain persists.

The key architectural consequence is that personal or organisational continuity does not need to live in a particular model, checkpoint, provider or compute substrate. Identity, autobiographical state, admitted memory, relationships, commitments, evidence and authority can persist in the sovereign domain while cognition remains replaceable.

Njål immediately accepted the reduction and instructed: `Bygg`.

## Framleis convergence and terminology lock

On 2026-08-19, the continuity wording was challenged as too narrow. `continuity` describes persistence, but can imply a static thread or insufficiently express that the actor's state is continuously changing.

The working session therefore returned to the earlier TOFOO term **Framleis**, which had already been established through exploration of `er`, `blir`, persistence and transformation, together with the decision that the Nynorsk word should not be translated away.

The convergence was reached from a different direction in PEACE:

```text
govern the workspace, not the worker
  -> worker becomes replaceable
  -> intelligence becomes replaceable
  -> separate what persists from intelligence
  -> state is dynamic rather than frozen
  -> continuity is too narrow
  -> Framleis
```

The resulting PEACE formulation is:

> **Intelligence reasons. State changes. The actor is Framleis.**

This is not a retroactive invention of a new term. TOFOO had already named the concept; PEACE independently exposed why it is architecturally necessary.

The normative lock is recorded in `docs/peace-framleis.md`:

> **Framleis must not be translated or replaced.**

`continuity`, `persistence`, `trajectory`, `becoming`, `persistent state`, and similar English phrases remain explanatory approximations, not equivalent terms.

The existing implementation names `peaceContinuityKernel` and `continuityRoot` are retained for compatibility in the current demonstrator. They describe technical projections of Framleis and do not supersede the normative term.

## Implementation

The continuity reduction was then implemented in PR #54 as `peaceContinuityKernel`, including:

- continuity preserved across cognition and compute swaps;
- learning entering as candidate state before sovereign admission;
- admitted experience unable to capture authority or directly mutate governed state;
- hostile-worker checks for direct effect, stale authority, replay, state write, authority capture and self-promotion;
- irreducibility checks for actor identity, sovereign state, fresh authority, consequence boundary and receipt admission.

## Standing and authority symmetry reduction

Later in the same working session, the language around `principal` was challenged.

Njål Solland identified that `principal` carries an implicit power hierarchy that may not belong in the mature PEACE architecture, and then made the key reduction:

> **Standing flows. Authority stands for both AI and human.**

The implication is that PEACE should not encode permanent human-over-AI hierarchy into its normative actor model. Actor identity and actor kind are separate from standing. Standing is contextual, versioned and revocable. Authority follows current standing for an exact consequence rather than being inherited from substrate or historic role.

This produced the additional formulation:

> **No permanent hierarchy. Only explicit standing.**

The architecture was then encoded in `peaceStandingAuthority.ts` with the same deterministic authority evaluation for human, AI, organisation, factory and service actors. Actor kind confers no implicit authority; stale, revoked, expired, wrong-purpose or out-of-scope standing produces `DENY -> NULL EFFECT`.

The continuity kernel was also refactored to remove `principal` as an irreducible PEACE primitive. `principalId` became neutral `domainId`, and `PRINCIPAL` in the irreducible core became `ACTOR_IDENTITY`.

A dedicated architectural note was added as `docs/peace-standing-authority-symmetry.md`.

## Contribution attribution

The PEACE/VALO trajectory and the premises that made these deductions possible were developed in the joint working process between Njål Solland and ChatGPT.

The specific conceptual leap **"separate continuity from intelligence"** and the formulation **"The model thinks. The sovereign domain persists."** originated from ChatGPT (GPT-5.6 Sol) in that session.

The specific reduction that **`principal` encodes an unwanted permanent hierarchy**, together with **"Standing flows. Authority stands for both AI and human."**, originated from Njål Solland in the same session.

The term **Framleis** predates the PEACE continuity reduction and was already canonical in the TOFOO work. PEACE independently rediscovered the architectural need for the concept through the continuity/intelligence separation; Njål recognized the convergence and instructed that Framleis be used and locked rather than replaced by an English approximation.

This file exists to preserve that lineage rather than retroactively flatten the work into a single-author narrative.
