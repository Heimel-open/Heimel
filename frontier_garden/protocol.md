# Tofoo Frontier Garden v1 — swarm and adjudication protocol

Issue: #106

## Purpose

The Garden turns unresolved Tofoo questions into bounded research tasks without promoting model output into truth, canonical state, or authority.

```text
OPEN_QUESTION != CLAIM != RESULT != GOVERNED_STATE != AUTHORITY
```

The Garden is informative research under `AGENTS.md`. It does not define VALO runtime behavior.

## Inquiry objective

The Garden optimizes for **improvement in the state of understanding**, not for answer production or forced closure.

A factual `DON'T KNOW` is a valid outcome when the available state does not support a stronger conclusion. It can also identify a new **seed**: an unresolved question whose preservation has potential future value.

```text
DON'T_KNOW -> possible SEED
SEED != CLAIM
SEED != TRUTH
UNRESOLVED != FAILURE
```

A seed does not have to be solved immediately. Preserving the right unknown can be more valuable than manufacturing a conclusion.

## Unit of work

A frontier is a versioned representation of an unresolved research state. Each frontier contains:

- one or more inquiry axes: `WHAT`, `WHO`, `WHY`, `HOW`;
- the current bounded understanding;
- the unresolved gap;
- contradictions already visible in source material;
- a falsifier or decisive test;
- the smallest next gate that could reduce uncertainty;
- explicit source references;
- related frontiers;
- lineage metadata.

A frontier is not itself a scientific claim. `epistemic_status` records the status of the source-grounded understanding used to frame the frontier.

## Mandatory lineage header

Each frontier element must begin with a navigation-only `lineage_header` containing, in order:

1. `origin` — the source reference from which the element originates;
2. `parents` — direct lineage parents, empty for a root element;
3. `status` — exactly `speculative`, `question`, or `evidence-backed`;
4. `evidence_refs` — the ordered compact index of the element's registered `source_refs`.

The header makes swarm branches searchable without changing their body, epistemic status, revision lineage, or evidence. A branch remains a branch until explicitly adjudicated and promoted.

## Sterile task packet

The CLI may emit a packet for exactly one frontier and one role. A packet contains only:

- protocol and standing identifiers;
- selected frontier state;
- the selected role and role instruction;
- explicit source references already registered on that frontier;
- fixed research boundaries.

It must not include unrelated repository content, previous model responses, hidden target answers, private conversation history, or later adjudication results.

The packet is an input artifact, not a grant of standing.

## Swarm roles

### DERIVATION

Derive only what follows from the stated frontier state and source-grounded premises. Mark missing premises and unresolved steps. Do not introduce a new primitive without labeling it as a proposal.

### SYNAPSE

Search for non-obvious connections, reframes, candidate primitives, or bridges to other registered frontiers. Speculation is allowed but must remain explicitly hypothetical.

### FALSIFIER

Attack the current understanding. Identify the strongest disconfirming interpretation, missing control, invalid assumption, or experiment that would change standing.

### COUNTEREXAMPLE

Seek a concrete construction, trace, model, transformation, dataset, or scenario that would break the current hypothesis or claimed generality.

### BRIDGE

Test whether the selected frontier and one or more related frontiers are manifestations of the same deeper unresolved mechanism. A bridge is a candidate relation, not an ontology update.

## Candidate output discipline

Raw model output is preserved as a proposal. It must not update `frontier_registry.json` automatically.

A candidate should distinguish, where applicable:

- source-supported statement;
- derivation from source-supported premises;
- speculation or new primitive;
- counterexample;
- falsification proposal;
- unresolved dependency;
- explicit `DON'T KNOW` where the state does not support a stronger answer.

Model agreement does not establish truth. Novelty does not establish truth. A useful hypothesis does not acquire authority.

## Selection, retention and forgetting

A Garden review must not equate present score with future value. The following rules apply:

1. `LOW_CURRENT_UTILITY != DISPENSABLE`.
2. `UNCERTAIN != DELETE`.
3. Diversity, agreement and candidate frequency are observations, not selection authority.
4. Rare falsifiers and counterexamples are preserved before frequency is revealed.
5. A candidate may remain `KEEP_OPEN` or be represented as dormant work when evidence is insufficient.
6. `RETIRE` requires resolution, supersession or an explicit redundancy basis; low score alone is insufficient.
7. A demonstrated formed invariant may be protected while bounded plastic inquiry proceeds around it.
8. Cross-representation continuity requires explicit semantic binding; structural similarity alone is not enough.

Where candidate ranking is required, future compositional reach may be tested as a hypothesis. It must not become a universal pruning rule without held-out evidence.

## Twin replay boundary

Twin historical replay may classify whether a candidate appears derivable from a prior represented state. The result is evidence for adjudication only. It cannot establish that a proposal is true, genuinely novel, personally identical to anyone, or authorized for execution.

## Adjudication

A human or separately governed review process may classify a proposed frontier change as:

- `ACCEPT` — incorporate a bounded change into a new frontier revision;
- `REJECT` — preserve the candidate as rejected evidence, do not change the frontier;
- `UNRESOLVED` — candidate is interesting but standing is insufficient;
- `KEEP_OPEN` — preserving the unresolved frontier is deliberately the best next state; do not force closure;
- `SPLIT` — one frontier should become multiple independently testable questions;
- `LINK` — add or revise a relation between frontiers without changing claim standing;
- `RETIRE` — the question is resolved, superseded, or no longer useful.

No adjudication may silently change a source claim's Tofoo epistemic status. Claim maturity remains governed by the existing claim/experiment registries.

Research-state acceptance is not action authorization. Garden state changes remain informative research and expose no consequence-bearing effect path.

## Framleis / lineage

Accepted changes create a new revision with:

- incremented `lineage.revision`;
- `parent_revision` pointing to the prior revision;
- a bounded `change_note` describing what changed and why.

The continuity question is:

> Is this still a trustworthy continuation of the represented research state?

Lineage may establish provenance and continuity of the representation. It does not establish truth, personal identity, scientific validity, or authority.

## Working loop

```text
registered frontier
  -> sterile packet
  -> fresh independent work
  -> raw output preserved
  -> adjudication
  -> ACCEPT / REJECT / UNRESOLVED / KEEP_OPEN / SPLIT / LINK / RETIRE
  -> if accepted: new lineage-preserved revision
```

## Swarm use

Multiple fresh models may receive the same packet independently. Their outputs should remain separate until preserved. Frequency may be recorded after preservation, but majority vote must not suppress rare falsifiers, counterexamples, high-leverage proposals, or well-grounded `DON'T KNOW` outcomes.

A swarm may also be allocated across roles rather than duplicating one role. The Garden therefore supports both breadth across models and diversity across cognitive operations.

## Non-goals

The Garden does not:

- execute tools or actions;
- mint authority;
- convert model confidence into evidence;
- make a digital representation the represented person;
- replace `CLAIM_REGISTRY.md`, experiment registries, or falsification records;
- declare a hypothesis validated because a model produced it;
- define production VALO architecture.
