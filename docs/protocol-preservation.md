# Protocol Preservation

Status: internal working note
Date: 2026-07-01

## Core claim

Meaning is instructional.

A system has not preserved meaning if it preserves facts but changes the action people or agents are expected to take.

Working formula:

```text
Meaning = Facts + Semantics + Instruction
```

Protocol is therefore not separate from meaning.

Protocol is one dimension of meaning.

## Why this matters

Most AI systems try to preserve information.

GEA / VAIG must preserve meaning through transformation.

A transformation can be:

- factually correct
- grammatically correct
- policy-compliant
- structurally coherent

and still fail if it changes the expected action-system.

That failure is a governance failure.

## Dugnad test case

The Norwegian word "dugnad" can often be translated as "volunteer work".

This preserves some visible facts:

- people showed up
- nobody was paid
- work was completed
- the community benefited

But it loses the protocol:

- social obligation
- reciprocity
- belonging
- collective ownership
- implicit responsibility
- local legitimacy
- cultural contract

The translation is factually acceptable but socially wrong.

It changes what the concept causes people to understand and do.

## Governance question

The relevant governance question is not only:

```text
Is the transformation true?
```

It is:

```text
Did this transformation preserve what the original meaning was supposed to cause someone to understand and do?
```

## Architectural position

Protocol Preservation should not initially be treated as a separate isolated layer.

It is better positioned as a cross-cutting governance property.

It should be evaluated across the full transformation pipeline:

```text
request
  -> interpretation
  -> model reasoning
  -> RAG
  -> tool calls
  -> agent handoff
  -> policy rewrite
  -> refusal / escalation
  -> final response
```

If any step preserves the facts but changes the expected action, meaning has degraded.

## Relation to Semantic Preservation / Framleis

Semantic Preservation asks whether meaning survived.

Protocol Preservation asks whether the instructional part of meaning survived.

Framleis can therefore be read as:

```text
Framleis = preservation of meaning, including the protocol of action, across transformation
```

## VAIG implication

GEA / VAIG governs semantic transformations, not text output.

A response is not fully admissible merely because it is true.

It must also preserve the action-protocol embedded in the original request, concept or instruction.

## Current status

This is a working governance principle.

Needed next:

1. define test cases for culture-bound protocol loss,
2. define measurable protocol-preservation criteria,
3. test translation, summarization and agent handoff failures,
4. decide how protocol preservation should appear in receipts,
5. integrate with `docs/semantic-preservation-layer.md`.
