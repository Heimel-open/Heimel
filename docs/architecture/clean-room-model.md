# Heimel clean-room model

Heimel can be understood as a governed clean room around consequence-bearing execution.

The objective is not to govern every internal reasoning step. The objective is to govern what may enter, how capabilities and communication may propagate inside, and what may leave as a real-world consequence.

```text
WORLD
  ↓
[ DOOR ]
identity • provenance • admissibility • authority context
  ↓
[ UNIFORM ]
bounded role • workspace • capabilities • purpose
  ↓
[ SCRUB ]
remove or normalize unsafe, stale or untrusted state
  ↓
[ GATE ]
admit into governed workspace
  ↓
┌──────────── CLEAN HOUSE ────────────┐
│                                     │
│ reasoning                           │
│ planning                            │
│ simulation                          │
│ memory                              │
│ internal computation                │
│                                     │
│ freedom inside, provided that:      │
│ - no real-world effect path exists  │
│ - communication is mediated         │
│ - authority is non-transferable     │
│ - tools are non-transitive          │
│ - secrets/capabilities do not leak  │
│ - cross-workspace sharing governed  │
│                                     │
└─────────────────────────────────────┘
  ↓
[ CHECK-OUT ]
exact proposed consequence
→ fresh authority
→ current constraints
→ exact effect binding
→ Gateway
→ real-world effect
→ Veritas
→ state admission / settlement
```

## Boundary model

### 1. Check-in: door

Before state or a principal enters a governed workspace, Heimel establishes the relevant identity, provenance, admissibility and authority context.

Admission does not grant indefinite execution authority. It establishes the bounded context in which internal work may occur.

### 2. Uniform

The admitted principal receives a bounded role, workspace, purpose and capability set. Capabilities belong to the binding that granted them; they do not become ambient properties of the room.

A tool, credential, secret or authority held by one principal is not inherited by another principal merely because they can communicate.

### 3. Scrub

Unsafe, stale, malformed or untrusted state must be rejected, transformed under explicit provenance, or kept non-consequence-bearing. Scrubbing must not silently create authority or erase material provenance.

### 4. Gate

Admission into the clean house is explicit. Workspace boundaries remain meaningful after admission and are not dissolved by shared context, shared memory, messaging or collaboration.

### 5. Inside the house

Internal reasoning is intentionally freer than consequence execution. A system may reason, plan, simulate, revise, remember and collaborate without requesting consequence authorization for every internal step.

This freedom is bounded by three normative invariants:

**NO_DIRECT_EFFECT_PATH**  
No principal inside the clean house may reach a real-world consequence target except through the governed Gateway path.

**NO_IMPLICIT_CAPABILITY_TRANSFER**  
Communication does not transfer authority, tools, credentials, secrets or other consequence-bearing capabilities. Capability-bearing transfer requires an explicit governed authorization and mediated transfer path.

**NO_UNGOVERNED_CROSS_WORKSPACE_PATH**  
Communication or state transfer across workspace boundaries must traverse a governed, attributable mediation path. Shared infrastructure must not collapse workspace isolation.

These invariants apply to deployed IAM, credentials, network paths, databases, service accounts, adapters and administrative paths, not merely to application source code.

### 6. Check-out

Every attempted transition from internal state to external consequence is a new boundary event.

Check-out evaluates the exact proposed consequence against current authority and current constraints. Authority is resolved fresh at consequence time; admission-time authority is not a reusable execution ticket.

The minimum consequence path is:

```text
exact proposed consequence
→ REHT fresh authorization
→ exact RACS binding / permit semantics
→ Gateway exclusive enforcement
→ external effect
→ Veritas effect/outcome evidence
→ Kernel state admission
→ optional consequence settlement
```

The governing question is:

> Does this principal, in this current state, have authority for this exact consequence now?

## What Heimel does not require

Heimel does not require inspection or approval of every internal thought, model token, plan revision or simulation step.

The control objective is narrower and stronger: preserve the boundaries around admission, capability propagation, workspace relations and real-world consequence.

## Operational interpretation

The clean-room model is only satisfied when the deployed system preserves the same boundaries. A source-level design is insufficient if a service account, raw database credential, cloud IAM permission, vendor token, network route or human administrative path bypasses Gateway.

Likewise, internal collaboration is not conformant if one principal can lend another its authority, tool access or secrets implicitly through messaging or shared workspace state.

The intended operational pattern is therefore:

```text
check-in
→ bounded workspace
→ internally free computation
→ mediated relations and explicit capability transfer
→ check-out
→ governed consequence
→ evidence
```

Heimel governs the transition between freedom inside the clean room and consequence outside it.
