# L0 Inference Layer

Status: draft v1.0
Scope: layer specification
Boundary: L0 has no execution authority

## Purpose

L0 produces candidate transitions.

It may reason, plan, generate text, propose tool calls or construct action plans.

It does not authorize execution.

## Examples

- LLM
- agent
- planner
- reasoner
- tool executor
- workflow engine

## Input

- current task
- prompt or instruction
- current context available to the model
- tool descriptions
- memory or retrieval context

## Output

L0 emits a candidate object:

- text output
- JSON object
- tool call
- action packet
- plan
- state transition proposal

## Contract

```text
L0 proposes.
L0 never commits governed execution.
```

## Prohibited responsibility

L0 must not be treated as the source of:

- authority
- final policy interpretation
- execution legitimacy
- receipt integrity
- state commit

## Handoff

L0 output must be passed to L1 Phi Runtime for projection and admissibility evaluation before any governed execution occurs.
