# LifeOS pattern adoption into VALO AI Work OS

Date: 2026-08-08
Status: canonical design adoption
Source signal: https://github.com/danielmiessler/LifeOS
Factory counterpart: nsolland/valo-factory#62

## Decision

Adopt the useful LifeOS Work OS patterns into VALO AI Work OS as native VALO contracts.

LifeOS is not a required runtime dependency, authority source or policy engine. The Operator remains the operational surface over registered Functions, domain packs and fresh Kernel context. REHT remains the sole final authorization boundary for consequence-bearing execution.

## Canonical convergence loop

```text
Current State
  -> evidence-backed Operator/Kernel snapshot
Ideal State
  -> explicit desired outcome + acceptance criteria
Gap
  -> candidate work / workflow / capability
Discover / Harvest
  -> evidence + adoption proposal
Factory
  -> BuildOrderV1 -> implementation -> tests -> independent judgment
Promote
  -> versioned Work OS artifact
Operate
  -> Operator -> fresh context -> REHT -> Gateway
Verify
  -> Veritas -> BARO -> Kernel
Learn
  -> persistent memory / Observation / next BuildOrder proposal
```

## Adopted patterns

### Current State -> Ideal State

Every meaningful Work OS objective should be representable as:

- an explicit Current State derived from fresh observable state;
- an explicit Ideal State containing the desired outcome;
- acceptance/postcondition criteria that determine whether the gap is actually closed;
- evidence linking the observed result to the exact objective and execution.

Workflow completion is not equivalent to goal completion. `success=True`, HTTP 200, a completed job or an agent saying "done" does not close the gap unless the required postcondition is independently observed.

### Persistent work memory

Work OS may persist:

- prior decisions and rationale;
- observations and verified outcomes;
- unresolved gaps;
- artifact/version references;
- failed attempts and regressions;
- user/domain preferences that are appropriate to retain;
- learned routing or workflow suggestions.

Memory is context and evidence only. It cannot create mandate, delegation, permission or clearance, and it cannot revive expired or revoked authority.

Fresh runtime state always wins over memory.

### Capability-aware routing

Before dispatch, orchestration should resolve the actual available capabilities and providers rather than assuming one model or one vendor.

Routing may consider:

- required capability;
- task/effect class;
- provider availability and entitlement;
- context-window/tool requirements;
- cost/latency policy;
- evidence requirements;
- required reviewer independence.

Routing selects a worker. It never selects or creates authority.

### Independent judgment

For consequential or high-impact work, Judgment/Review should prefer a different provider or model family from the Writer/Execution provider when the available provider set allows it.

This is a correlated-error control, not a second authorization system.

Judgment produces findings, evidence and a promotion recommendation. It cannot grant runtime execution authority.

### Harvest-style discovery and adoption

External sources may be harvested into the Work OS improvement loop:

```text
source
-> extract candidate concepts
-> compare with canonical VALO contracts
-> classify: already-covered / partial / new
-> identify exact owner repo + integration point
-> produce evidence-backed adoption proposal
-> BuildOrderV1 when implementation is required
```

Harvest never mutates production architecture directly and never auto-activates a capability.

### Verify -> Learn

Learning follows observed outcome, not provider assertion.

A learning entry should bind, as applicable:

- objective / Ideal State ref;
- Current State digest;
- exact Function/version and workflow instance;
- REHT decision/permit reference;
- execution receipt;
- observed postcondition/effect evidence;
- BARO result;
- conclusion and confidence;
- proposed next action or BuildOrder.

The learner can propose change. It cannot self-authorize the change.

## Relationship to Factory OS

Factory OS owns construction, tests, independent review and artifact promotion. Work OS owns the operational capability surface and fresh business context.

```text
Factory OS builds what Work OS can do.
Work OS exposes what can be requested.
REHT decides what may happen now.
Veritas/BARO proves what actually happened.
Learning proposes what should change next.
```

## Explicit non-adoption

Do not adopt any pattern that collapses these roles into one self-authorizing agent:

- orchestration;
- discovery;
- execution;
- judgment;
- runtime authorization.

They may cooperate through explicit contracts and evidence, but REHT remains separate from model reasoning and from Work OS memory.

## Acceptance invariants

1. Current State is derived from fresh state/evidence, not memory alone.
2. Ideal State is explicit enough to verify.
3. Workflow completion cannot substitute for observed postcondition.
4. Persistent memory cannot grant or revive authority.
5. Capability routing is provider-neutral and carries no authorization semantics.
6. High-impact judgment prefers provider independence when available.
7. Harvest outputs proposals/evidence, not direct production mutations.
8. Learning requires observed outcome evidence.
9. Self-improvement re-enters through Factory governance rather than modifying live runtime directly.
10. REHT remains the sole final authorization boundary for consequence-bearing execution.
