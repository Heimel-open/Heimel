# HEIMEL Architecture

**Intent. Realized.**

HEIMEL governs the transition from intent to consequence.

```text
Anything that forms intent → HEIMEL → Anything that causes effect
```

## Minimum consequence path

The architecture is property-based, not component-count-based:

```text
authoritative operative state + exact proposed effect
→ fresh authorization
→ deterministic decision/effect binding
→ exclusive governed effect
→ effect/outcome proof
→ state admission
```

Current owner mapping:

```text
Kernel operative state + exact proposed effect
→ REHT fresh authorization
→ Gateway mechanical enforcement
→ external effect
→ Veritas proof
→ Kernel state admission
```

RACS is the deterministic decision/action/permit/receipt contract carried across REHT, Gateway and Veritas. It is not an active runtime service hop.

## Universal property owners

### Kernel

Owns admitted operative state, authority and delegation records, deterministic events and replay, and evidence-backed state admission.

Kernel does not authorize or execute external effects.

### REHT

Owns the sole fresh authorization decision for the exact proposed effect against current operative state, authority, scope, purpose, constraints and required evidence.

REHT does not mutate the external system.

### RACS

Defines the stable deterministic binding between the established decision, exact effect, one-shot permit and receipt requirements.

RACS does not evaluate, authorize, enforce, execute or store evidence.

### Gateway

Mechanically validates current bindings, consumes the one-shot permit, prevents replay and bypass, and invokes the exact authorized effect.

Gateway has no independent policy judgement. `NO_DIRECT_EFFECT_PATH` is absolute.

### Veritas

Preserves integrity-protected, attributable evidence of the effect and observed outcome. Evidence is not retroactive authorization and does not become operative state without admission.

## Conditional capabilities

| Capability | Use | Boundary |
|---|---|---|
| Workflow ISA | Deterministic process semantics, branching, WAIT/resume and workflow state | No authority or direct consequence |
| Function Fabric | Typed, versioned governed Functions and lowering onto workflow semantics | Capability definition is not permission |
| VAIG | Evaluation of uncertainty, risk, quality and evidence when required | Evaluation is not authorization |
| MAL | Admission of an exact model/runtime profile before invocation | Model-use admissibility is not effect authorization |
| GCoP / Open Agent Contract | Bounded handoff, delegation, scope, constraints and completion contracts | Conformance is not authorization |
| PEACE | Sovereign-domain authority-state/evidence interoperability | Separate protocol; no VALO runtime ownership |
| ACE | Economic and human-attention research | No protocol or authority role |

A governing contract may require one or more conditional capabilities. Their use does not make them universal runtime hops.

## Public reference packages

The public repository contains curated Apache-2.0 packages:

- `packages/kernel` — minimal operative-state, replay and admission core
- `packages/workflow-isa` — typed deterministic workflow semantics
- `packages/function-fabric` — provider-neutral governed Function composition

Canonical runtime ownership remains in `nsolland/valo-kernel`, `nsolland/valo-workflow-isa` and `nsolland/valo-function-fabric`. HEIMEL owns the public distribution, not a second runtime implementation.

Provider adapters, credentials, customer policy, calibration, deployment internals and private product code are outside this public surface.

## Boundary invariants

1. **No direct effect path.** Consequence-bearing actions pass through the governed boundary.
2. **Fresh authority.** The exact effect is authorized against current operative state at consequence time.
3. **Exact binding.** Decision, effect, permit and receipt remain deterministically correlated.
4. **Fail closed.** Missing, stale or mismatched material authority, state, evidence or binding cannot silently execute.
5. **Evidence by construction.** Effects and outcomes remain attributable and replayable.
6. **State requires admission.** A receipt or provider response cannot directly mint operative state.
7. **Model independence.** Models, workers and orchestration may change without moving the consequence boundary.

## Still open

The reference packages are public and locally validated. The following are not yet claimed complete:

- immutable version tags and published package artifacts;
- SDK, CLI and standalone verifier;
- a coherent public end-to-end install and execution demo;
- clean-room VAIG and MAL public reference surfaces;
- selected domain packs and integration examples after their own release gates.
