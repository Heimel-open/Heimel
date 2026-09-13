# Tofoo Frontier Garden v1

Issue: #106

The Frontier Garden is a living, machine-readable map of unresolved Tofoo research questions that humans and independent model swarms can work on over time.

It is an **inquiry and continuity layer**, not a truth or authority layer.

```text
OPEN_QUESTION != CLAIM != RESULT != GOVERNED_STATE != AUTHORITY
```

## Why this exists

Tofoo already contains hypotheses, formal definitions, experiments, falsification criteria and unresolved mechanism gaps. The Garden makes those unresolved points directly addressable without requiring a model to ingest the whole repository or silently promote its own output.

## Seed principle

The Garden treats a precise `DON'T KNOW` as a potentially valuable research state rather than a failed answer.

> **KNOWN tells me what I can use.  
> DON'T KNOW tells me where value may still be hiding.**

```text
DON'T_KNOW -> possible SEED
SEED != CLAIM
SEED != TRUTH
UNRESOLVED != FAILURE
```

A **seed** is an unresolved question worth preserving because further work may change the state of understanding. The Garden does not require every seed to be resolved, and it does not reward closure for its own sake. A valid next state may be to keep the question open, sharpen it, split it, connect it to another frontier, or identify what evidence is missing.

The working loop is:

```text
frontier state
  -> sterile task packet
  -> independent candidate work
  -> preserved raw output
  -> adjudication
  -> accepted/rejected/unresolved change
  -> lineage-preserved frontier state
```

A model may derive, speculate, falsify, propose counterexamples or connect separate frontiers. None of those operations gives the output epistemic standing by itself.

## Retention and formation rules

The 2026-08-21 Synapse/Twin synthesis adds six operating constraints:

- current isolated utility is not a sufficient proxy for future compositional value;
- generic diversity is not automatically useful and must remain falsifiable;
- uncertain latent candidates may remain open or dormant rather than being deleted;
- deletion should use an explicit redundancy certificate where one is available;
- formed and demonstrated invariants may be protected while plastic search continues around them;
- continuity across representations requires correct semantic binding, not byte or coordinate similarity alone.

Twin replay may test whether a candidate was already derivable from prior represented state. It does not decide truth, novelty, personhood or authority.

## WHAT / WHO / WHY / HOW

Each frontier has one or more inquiry axes:

- `WHAT` — what is the object, phenomenon, distinction or state?
- `WHO` — who/what is the actor, observer, representation or bearer of a property?
- `WHY` — what explanation, cause, objective or dependency is missing?
- `HOW` — what mechanism, test or implementation could resolve the uncertainty?

The axes are navigation metadata, not ontology.

## Mandatory lineage header

Every frontier element begins with one navigation-only `lineage_header` in this fixed order:

`origin -> parents -> status -> evidence_refs`

`status` is exactly one of `speculative`, `question`, or `evidence-backed`. The header indexes provenance and standing; it does not move, rewrite, merge, or promote the frontier content. `evidence_refs` mirrors the element's registered `source_refs` in order.

## Framleis / lineage role

The Garden records how the **representation of current understanding** changes over time. That lineage can support a Framleis-style continuity question:

> Is this still a trustworthy continuation of the represented research state?

It does **not** establish that a claim is true, that a representation is a person, or that any actor has authority.

## Swarm roles

A task packet may ask a fresh model to operate in one role:

- `DERIVATION` — derive only what follows from stated premises.
- `SYNAPSE` — seek new connections, reframes and candidate primitives.
- `FALSIFIER` — find the strongest disconfirming argument or test.
- `COUNTEREXAMPLE` — search for a concrete case that breaks the claim/model.
- `BRIDGE` — test whether two frontiers are manifestations of the same deeper problem.

Raw outputs are proposals. They must not update the registry automatically.

## Files

- `frontier_registry.json` — canonical Garden v1 working registry.
- `frontier.schema.json` — JSON Schema for registry validation.
- `protocol.md` — swarm/adjudication protocol.
- `research_synthesis_2026-08-21.md` — bounded source state for FG-011 through FG-020.
- `../scripts/frontier_garden.py` — zero-dependency CLI.

## CLI

```bash
python3 scripts/frontier_garden.py validate
python3 scripts/frontier_garden.py list
python3 scripts/frontier_garden.py show FG-001
python3 scripts/frontier_garden.py packet FG-003 --role SYNAPSE
```

`packet` writes a sterile JSON task packet to stdout. It contains the selected frontier, its explicit source references and the requested role instructions — not unrelated repository context.

## Epistemic boundary

The repository `AGENTS.md` remains controlling. Every research claim keeps exactly one allowed Tofoo epistemic status. The Garden adds no new scientific maturity level and no runtime standing.
