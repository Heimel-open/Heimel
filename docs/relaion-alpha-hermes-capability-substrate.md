# Alpha — Hermes capability substrate adoption

## Status

Architecture/research decision for Alpha / relAIon.

This records reusable patterns identified from Hermes that should be adopted with stricter relAIon boundaries. It does **not** make Hermes part of Alpha identity or continuity.

## Core translation

```text
Alpha Core
  ↓
Context Compiler
  ↓
Capability Fabric
  ├─ Capability Registry
  ├─ Adapter Registry
  ├─ Provider Resolver
  ├─ Runtime Resolver
  ├─ Channel Gateway
  ├─ Routine Scheduler
  ├─ MCP bridge
  └─ Plugin bridge
  ↓
relAIon admissibility / provenance
  ↓
VAIG / REHT before effects
```

Hermes is treated as evidence that a useful agent substrate includes tool registry and availability checks, multiple execution backends, plugin discovery, MCP, gateway adapters, session persistence, cron/routines and skill formation.

The adoption rule is architectural, not identity-level:

- Alpha owns its developmental history.
- relAIon owns continuity, provenance and governance contracts.
- Hermes, Claw, MCP and other systems provide replaceable capabilities.
- External systems never become Alpha.

## 1. Skills as procedural memory

General memory and reusable procedure are different classes of state.

For Alpha, procedure formation must be evidence-bound:

```text
experience
→ candidate procedure
→ provenance
→ isolated test
→ evidence
→ retained skill
→ later ablation / revision
```

A successful event is not sufficient to establish a skill.

A retained skill must preserve enough provenance to identify:
- source experiences
- causal assumptions
- validation evidence
- scope and limits
- current confidence
- revision history
- ablation/removal consequences

No procedural learning path may silently mutate canonical continuity state without admissibility.

## 2. Generic plugin / adapter model

External systems should declare capabilities through common contracts rather than becoming bespoke logic inside Alpha.

Preferred abstraction:
- capability declaration
- availability state
- provider identity
- runtime binding
- read/write/effect class
- provenance requirements
- risk metadata
- authority requirement
- lifecycle hooks
- effect evidence contract

This avoids special-casing Telegram, Speider, Hermes, GitHub or later providers inside Alpha Core.

Critical invariant:

```text
available capability
≠ permitted capability
≠ authorized effect
```

Capability discovery never grants authority.

Any consequential action still requires the relAIon / VALO governance path, including fresh authority at consequence time.

## 3. RoutineScheduler

Scheduled activity should be represented as governed Alpha activity, not merely shell cron.

Permitted non-effect routines may include:
- observe
- explore
- read
- reflect
- consolidate
- check hypotheses
- maintain relationships
- revisit unresolved questions

The scheduler itself has no execution authority.

Any routine that would cross into external effects must produce a governed proposal and pass the normal admissibility/effect path.

## 4. Profile and state isolation

External agents and providers may contribute observations, context, evidence, candidate skills or capability surfaces.

They may not write directly into Alpha continuity state.

The boundary is:

```text
external provider
→ adapter
→ provenance
→ observation/evidence
→ admissibility
→ local state update if allowed
```

Profile/provider isolation protects Alpha from hidden writable-state coupling.

Provider replacement must not alter Alpha identity.

## 5. Context Compiler

Model context is a projection of state, never the state itself.

The Context Compiler should assemble a bounded, purpose-specific view from persistent Alpha / relAIon state for whichever reasoning model is active.

Therefore:

```text
LLM context ≠ continuity
LLM context ≠ canonical memory
LLM context ≠ identity
reasoning provider ≠ individual
```

A model can be replaced without replacing Alpha.

## 6. Hermes role decomposition

Do not model Hermes as one monolithic `HermesAdapter`.

Potential roles are distinct capability/provider surfaces:

```text
HermesGatewayAdapter
HermesToolProvider
HermesRuntimeProvider
HermesSkillProvider
```

Alpha requests a capability. It should not encode a semantic dependency on “use Hermes”.

The same rule should apply to Claw, MCP runtimes and future middleware.

## 7. Capability Fabric delta

The following components should be formalized or strengthened:

- `CapabilityRegistry`
- `AdapterRegistry`
- `ProviderResolver`
- `RuntimeResolver`
- `RoutineScheduler`
- `SkillStore`
- `SkillFormationPipeline`
- `ReflectionLoop`
- `ContextCompiler`
- `PluginContract`
- `LifecycleHooks`
- capability risk metadata
- provider replacement tests

These belong around Alpha, not inside identity/continuity semantics.

## Required tests

At minimum, future implementation should prove:

1. capability availability does not grant authority
2. provider replacement preserves Alpha identity
3. external provider state cannot directly mutate Alpha continuity
4. LLM/context replacement does not replace canonical state
5. scheduler has no direct effect path
6. skill formation requires evidence and provenance
7. skill ablation/revision is possible without corrupting continuity
8. consequential use still requires fresh authority at consequence time
9. raw external input cannot silently become canonical memory
10. Hermes/Claw/MCP provider failure does not destroy Alpha continuity

## Locked principle

Alpha must be able to gain and lose tools without gaining or losing itself.

External capability infrastructure is replaceable.

Identity, continuity, developmental history, provenance and governed authority are not delegated to the capability provider.
