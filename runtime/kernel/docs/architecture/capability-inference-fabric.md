# Capability / Inference Fabric

Status: adopted architecture principle

External reference: Superlinked SIE (Apache-2.0)
https://github.com/superlinked/sie

## Principle

Inference is a replaceable capability fabric. Authority is not.

A governed system MUST keep model selection, loading, routing, inference, retrieval, extraction, reranking, guard evaluation, and agent-loop execution logically separate from authority to create external consequence.

A capability provider MAY expose many heterogeneous models behind one stable API and MAY dynamically select, load, unload, route, or replace those models without changing the authority contract.

No capability provider, model server, router, agent runtime, or inference cluster acquires consequence authority merely because it produced, selected, scored, or executed a proposed action.

## Adopted pattern from SIE

SIE demonstrates a useful commodity-inference pattern:

- one stable API over heterogeneous models;
- task-oriented capability classes rather than model-specific application coupling;
- on-demand model loading and eviction;
- interchangeable local/self-hosted execution;
- one inference surface spanning embeddings, retrieval/reranking, document conversion, structured extraction, guard models, and generation/agent loops.

VALO adopts the architectural pattern, not SIE as a required dependency.

## VALO boundary

The resulting separation is:

    capability request
          |
          v
    Capability / Inference Fabric
    - select capability/model
    - execute inference
    - return proposal/evidence
          |
          v
    VAIG / admissibility
          |
          v
    REHT
    - resolve authority fresh at consequence time
          |
          v
    RACS
    - ALLOW / DENY / ESCALATE
          |
          v
    governed Gateway / PEP
          |
          v
    external consequence
          |
          v
    Veritas / evidence

The inference fabric ends at proposal/capability output. It has no direct effect path.

## Invariants

1. INFERENCE_IS_NOT_AUTHORITY
   Model execution never implies permission to act.

2. CAPABILITY_IS_REPLACEABLE
   A model, model family, runtime, router, or inference server may be replaced without changing the consequence-authority semantics.

3. NO_DIRECT_EFFECT_PATH
   Capability output cannot bypass the governed consequence path.

4. FRESH_AUTHORITY_AT_CONSEQUENCE_TIME
   Authority is resolved after capability execution and immediately before governed effect.

5. MODEL_ROUTING_IS_NON_AUTHORITATIVE
   Dynamic routing, fallback, eviction, scaling, and model selection are operational decisions, not grants of authority.

6. EVIDENCE_SURVIVES_MODEL_SUBSTITUTION
   Consequence evidence records the capability/model provenance needed for replay or audit without making a particular model authoritative.

## Product implication

This permits VALO to treat inference infrastructure as commodity while retaining the non-commodity layer: authoritative state, admissibility, consequence-time authority resolution, deterministic decision semantics, governed effects, and verifiable evidence.

The same boundary supports local governed agent deployments: private local inference can evolve independently of persistent identity/context and independently of the right to create consequence.

Conceptually:

    inference fabric -> interchangeable capability
    persistent domain -> identity/context continuity
    REHT/RACS       -> right to consequence
    governed effect -> externally meaningful action

The architecture MUST preserve these boundaries even when all components run on one physical device.
