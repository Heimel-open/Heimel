# Semantic Preservation / Protocol Preservation

Status: internal working note
Date: 2026-07-01

## Core idea

VAIG should not only govern text, format, policy or execution.

VAIG must also preserve meaning across transformation.

A transformation can be grammatically correct, policy-compliant and still fail if it changes what people or agents are expected to understand and do.

Core rule:

```text
Allow iff meaning_preserved(request -> response)
```

More precise form:

```text
Allow iff semantic_identity(source_concept) ~= semantic_identity(output_concept)
```

## Meaning is instructional

Working hypothesis:

```text
Meaning = Facts + Semantics + Instruction
```

Facts alone are not enough.

If a transformation preserves the factual content but changes the expected action, meaning has not been preserved.

Protocol is therefore not separate from meaning. Protocol is one dimension of meaning.

## Protocol Preservation as cross-cutting property

Protocol Preservation should not initially be treated as a separate architectural layer.

It is better understood as a cross-cutting governance property that must be evaluated throughout the transformation pipeline.

It should be checked across:

- request interpretation
- translation
- summarization
- RAG retrieval and synthesis
- tool calls
- agent-to-agent communication
- model routing
- policy rewriting
- refusal handling
- final response generation

Governance question:

```text
Did this transformation preserve what the system was supposed to cause someone to understand and do?
```

## Why metadata is not enough

Runtime identity can describe:

- model id
- checkpoint
- provider
- routing path
- system prompt hash
- policy profile
- tools
- RAG sources
- context window
- sampling parameters

This is necessary, but not sufficient.

It tells us who executed the transformation.

It does not prove that meaning survived the transformation.

## Framleis

Working definition:

```text
Framleis = preservation of meaning across transformation
```

Framleis is not simple continuity of text. It is semantic and instructional continuity.

The governance question is:

```text
Is the meaning still the same after the system transformed it?
```

## Culture-bound meaning

Some words are not cleanly translatable into another language without semantic loss.

Examples:

- framleis
- dugnad
- kos
- hygge
- lagom
- saudade

For example:

```text
framleis != still
```

"Still" may be a valid dictionary translation, but it does not fully preserve the Norwegian sense of continuation, persistence and identity-through-time.

Likewise:

```text
dugnad != volunteer work
```

"Volunteer work" captures part of the action, but not the collective civic and cultural frame.

## Dugnad as test case

A translation chain may preserve all visible facts:

- people showed up
- nobody was paid
- work was completed
- the community benefited

But if "dugnad" becomes "volunteer work", the protocol is degraded.

What disappears is:

- social obligation
- reciprocity
- belonging
- collective ownership
- implicit responsibility
- the cultural contract

The translation is factually correct, but socially wrong.

That is a governance failure.

## VAIG implication

VAIG should govern semantic transformations, not only output strings.

If wording, format and policy are preserved but meaning is degraded, the transformation is not fully admissible.

If facts are preserved but the expected action changes, the transformation is not fully admissible.

## Proposed stack placement

Protocol Preservation should be cross-cutting rather than a single isolated layer.

```text
Runtime Identity
  -> Semantic Preservation / Framleis
  -> Structural Coherence / tau
  -> Temporal Validity / TAD
  -> Governance / VAIG / MECHA
  -> Receipt / WORM / Audit
```

But Protocol Preservation should be evaluated across all arrows, not only at one node.

## Boundary

This property does not claim to determine truth itself.

It checks whether the represented meaning of a request, concept or instruction remains sufficiently preserved through system transformation.

## Current status

This is a working governance property, not yet an implemented module.

Needed next:

1. define a measurable semantic / protocol preservation score,
2. test culture-bound terms across translation and summarization,
3. map failure cases where text is correct but meaning is lost,
4. map failure cases where facts are correct but expected action changes,
5. decide whether Framleis is best formalized as an operator, a cross-cutting property, or both.
