# Organization Projection Boundary

## Decision

A "Company Brain", organizational memory graph, RAG knowledge base, dashboard,
agent memory, or similar enterprise knowledge surface is a **derived read model**.
It is never a second world model and never a source of authority.

The VALO Kernel remains the only authoritative owner of governed world state.

## Why

Products can benefit from a living organizational view that combines company
profile, documents, past performance, team context, opportunities, outcomes and
analytical summaries. The useful pattern is one shared context surface reused by
matching, analysis, drafting and workflow decisions.

The failure mode is allowing that surface to become a parallel state owner. A
standalone "brain" that decides which facts are true, carries cached authority,
mutates business state, or becomes the source for execution creates a shadow
kernel with weaker provenance, time and conflict semantics.

## Classification

A product-level "Company Brain" may display several classes of information, but
they do not have the same status:

- **Canonical business state** — identities, entities, relationships, admitted
  capabilities, contracts, resources, authorities, rights, obligations,
  purposes and accepted outcomes belong in Kernel state.
- **Canonical process state** — go/no-go decisions, submitted work, accepted
  commitments and verified award/outcome state belong in governed workflow/world
  state, not in a private memory store.
- **Evidence awaiting admission** — documents, portal observations and external
  records remain evidence until verified and admitted through canonical events.
- **Analytical inference** — fit scores, predictions, summaries, gap analyses,
  suggested strategies and generated drafts are derived views. They remain
  `INFERRED` or presentation artifacts and never become truth by repetition.

The product may present all four together. Storage and authority must remain
separated even when the UI makes them look like one coherent brain.

## Contract

An organization projection MAY:

- materialize deterministic read views from a specific Kernel state root;
- join canonical entity, fact, relationship, evidence, resource and history
  references for retrieval and presentation;
- contain model-generated summaries and predictions when they remain explicitly
  `INFERRED`, carry provenance/evidence references, confidence and freshness;
- cache views for performance when the source state root and projection time are
  retained;
- propose new evidence, candidate facts or work items for normal admission.

An organization projection MUST NOT:

- own authoritative facts, identity, rights, obligations, purpose, authority or
  delegation independently of the Kernel;
- promote documents, embeddings, model output or retrieved text directly to
  `CONFIRMED` state;
- mutate WorldState directly;
- persist an execution permission as if it remained valid after the source
  Kernel state changed;
- authorize or execute external action;
- win a conflict with current Kernel state.

## Required envelope

Every projection used for governed work should retain enough information to
prove what it was derived from:

- `tenant_id`
- `source_state_root`
- `projected_at`
- canonical object/evidence/provenance references
- truth status for factual claims
- inference metadata for model-derived claims
- freshness or expiry where the claim can become stale

A knowledge page without this envelope is presentation only and must not be used
as an execution fact.

## Mutation path

```text
external document / observation / model output
        |
        v
Evidence / candidate claim
        |
        v
verify -> admit -> canonical Kernel event -> WorldState
                                      |
                                      v
                              Organization Projection
                                      |
                         query / match / analyse / draft
                                      |
                                      v
                         fresh execution context -> REHT
                                      |
                                  RACS -> Gateway
                                      |
                              Veritas -> BARO
                                      |
                               Kernel event
```

The learning loop therefore returns outcomes to the Kernel through evidence and
canonical events. The projection refreshes from the governed world; it does not
learn by silently rewriting its own truth.

## Staleness and conflict

If the projection's `source_state_root` no longer matches the state used for a
governed decision, the projection is stale for execution. It may still be useful
for exploration, but a fresh Kernel query/execution context is required before
REHT clearance.

If projection content conflicts with Kernel state, Kernel state wins and the
projection must expose or invalidate the conflict rather than reconcile it with
an LLM.

## Chromie pattern adopted

The useful product pattern is a shared organizational context feeding discovery,
fit assessment, capture analysis, drafting and lifecycle/outcome tracking. The
VALO adoption keeps that UX and learning-loop advantage while replacing the
"brain as truth" interpretation with a governed organization projection over
Kernel state.
