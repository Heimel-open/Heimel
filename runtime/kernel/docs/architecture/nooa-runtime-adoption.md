# NOOA runtime adoption

Status: adopted architectural guidance
Source: NVIDIA-labs Object Oriented Agents (NOOA), 2026

## Decision

VALO does not become an agent framework and does not absorb agent-internal working state into the governance kernel.

Agent runtimes such as NOOA remain responsible for reasoning, orchestration, live working state, model interaction, and capability invocation. VALO governs the boundary where proposed work can become a real consequence.

Canonical separation:

`agent runtime -> governed effect boundary -> fresh authority resolution -> admissibility decision -> effect -> evidence/replay`

For the current VALO stack this maps to:

`NOOA/other runtime -> VAIG -> REHT -> RACS -> Gateway/PEP -> Veritas`

The existing invariant remains unchanged: `NO_DIRECT_EFFECT_PATH`.

## Adopted principles

### 1. Live objects and pass-by-reference

Adopt NOOA's live-object/pass-by-reference approach as a preferred runtime pattern where it reduces serialization, token movement, and artificial context reconstruction.

This is an execution/runtime concern. Live object state is not authoritative merely because it is live.

At the consequence boundary, authoritative state MUST be resolved according to VALO's freshness and authority rules.

### 2. Deterministic vs model-driven methods

Preserve an explicit distinction between deterministic capabilities and model-driven/agentic capabilities.

The distinction improves inspectability and testing, but does not itself grant execution authority. Either class of capability MUST traverse the governed effect path when it can create an external consequence.

### 3. Separate agent loop from runtime/harness

Adopt the architectural separation between model reasoning and the runtime/harness that supplies state, capabilities, context, tracing, and execution mechanics.

VALO remains a separate governance layer rather than embedding governance semantics into model prompts or agent-loop conventions.

### 4. Event sourcing and transparency are complementary evidence

NOOA's event-sourced runtime, serialized execution, and tracing can provide useful upstream execution evidence.

Such traces are inputs to evidence and replay; they are not substitutes for consequence-time authorization, admissibility, effect receipts, or authoritative replay evidence.

## Integration contract

A runtime adapter MAY expose:

- proposed action/capability
- actor/agent identity
- purpose and task context
- typed arguments or references
- runtime event/trace identifiers
- relevant provenance

Before an external effect, VALO MUST independently resolve and evaluate the authority and constraints required for that consequence.

The runtime MUST NOT be able to bypass the Gateway/PEP for governed effects.

A successful internal method invocation, valid type contract, completed agent loop, or runtime trace MUST NOT be interpreted as execution authorization.

## Non-goals

VALO will not fork or reproduce NOOA merely to own an agent runtime.

VALO will not require NOOA specifically. The boundary is runtime-neutral and should support NOOA, SIE-like local runtimes, coding agents, hosted agent harnesses, and future runtimes through adapters.

## Architectural implication

Runtime innovation is expected to commoditize rapidly. VALO's durable responsibility is independent consequence governance across runtimes:

`reason anywhere; act only through governed consequence boundaries.`

## Source notes

NOOA represents agents as Python objects: fields as state, methods as capabilities, docstrings as prompts, and type annotations as contracts. It distinguishes deterministic Python methods from LLM-driven methods, supports live-object arguments passed by reference, and describes its runtime as using event sourcing, serialized execution, and transparency.

Upstream: https://github.com/NVIDIA-NeMo/labs-OO-Agents
