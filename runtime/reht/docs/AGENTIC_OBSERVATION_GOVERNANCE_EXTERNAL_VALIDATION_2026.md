# Agentic observation governance — external validation

Status: external architecture evidence
Source: Google, Gemini agentic video / active video understanding
Date recorded: 2026-09-02

## Why this matters

The material shift is not merely better video understanding. The model is moving from passive, fixed-rate ingestion toward active allocation of observation: deciding where to inspect, when to increase temporal or modal resolution, and when to revisit a segment.

That changes the governance boundary.

A consequential agent may increasingly determine not only what action to take, but what evidence to inspect before acting. Observation therefore becomes part of the governed decision path rather than a neutral preprocessing step.

## VALO implication

VALO currently treats authoritative state, fresh authority, constraints, commit-time authorization, execution, and evidence as distinct governed concerns. Active perception adds an upstream concern:

`Mandate -> Observation policy -> Selected evidence -> Decision -> REHT -> RACS -> Effect -> Veritas`

The important property is not that every observation must be centrally prescribed. It is that consequential observation choices must be reconstructable and bounded where omission can materially change the outcome.

## New governance question

For a consequential decision, evidence should distinguish at least:

- what information was available to the agent;
- what the agent actually inspected;
- what it deliberately or mechanically skipped;
- whether observation depth or modality changed during the task;
- whether omitted evidence was required by mandate, policy, law, or domain procedure;
- whether the final effect remained admissible given the observation path actually used.

This creates a class of failure that ordinary action logging cannot detect: the effect may be correctly authorized relative to the evidence the agent considered while the evidence-selection process itself was defective.

## Design principle

No direct effect path should eventually be paired with a weaker but analogous rule upstream:

> No materially consequential effect should rely on an ungoverned observation path when the mandate requires specific evidence, coverage, or inspection duties.

This does not mean forcing exhaustive observation. The point is selective compute with accountable selection.

## Relationship to selective compute

The same architecture that makes active perception efficient also makes selective compute a first-class systems concern:

`broad scan -> relevance estimate -> local resolution increase -> re-observe -> decide`

That fits a node/supernode architecture better than uniform frontier-model processing. Compute can be concentrated where uncertainty, consequence, or evidence obligations justify it.

The governance layer should therefore govern not only model/action admissibility, but potentially observation-budget admissibility as well.

## Evidence value

This is external validation of a direction rather than validation of VALO itself. It supports the claim that agentic control is moving downward into perception and resource allocation, making observation provenance and omission increasingly relevant to execution governance.

## Research consequence

Add an explicit observation/perception layer to future consequence-path models and tests. In particular, test cases should separate:

1. complete required observation + admissible action;
2. incomplete required observation + otherwise admissible action;
3. selective observation allowed by mandate + admissible action;
4. agent revisits evidence after uncertainty increases;
5. evidence omitted because of compute optimization where omission changes the decision.

The key falsifiable question is whether governing the observation path materially reduces incorrect-but-apparently-authorized effects without forcing exhaustive processing.