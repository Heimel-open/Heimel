# Coherence Sentinel - Nested Coherence Conflict

## Problem

Recursive coherence requires handling conflicts between layers.

A lower layer can remain locally coherent while an enclosing layer has lost coherence.

## Example

- Agent executes consistently.
- Runtime passes all checks.
- But the owning team may have drifted from stated purpose or stopped review discipline.

## Rule

Local coherence is not sufficient for global coherence.

A lower layer may not claim full clearance if an enclosing governance layer is incoherent or unknown.

This is the recursive version of UNKNOWN != SAFE:

UNKNOWN at any superior governance layer is not SAFE.

## Conservative Aggregation

global_coherence = min(
    agent_coherence,
    runtime_coherence,
    governance_stack_coherence,
    team_coherence,
    organization_coherence,
    institution_coherence,
)

This min rule is the first safe engineering rule, not final mathematics.

## Architecture Implication

Coherence Sentinel must observe both local process continuity and enclosing governance continuity.

## Authorizing Rule

You may not continue merely because you are locally coherent.

You may continue only if the layer authorizing you is also coherent enough to authorize continued action.

## Boundary

- Architecture docs first
- No runtime wiring yet
- No core implementation until measurable layer signals are defined
