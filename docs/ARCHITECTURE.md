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
| PEACE | Sovereign-domain authority-state/evidence interoperability | Separate protocol; no runtime authority |
| ACE | Economic and human-attention research | No protocol or authority role |

A governing contract may require one or more conditional capabilities. Their use does not make them universal runtime hops.

## Open execution boundary

Open Heimel contains everything required to understand, build, integrate, test and locally operate governed execution.

The migrated runtime universe is present under `runtime/`. `runtime/MIGRATION_MANIFEST.yaml` records source repositories and source commits for Kernel, REHT, Gateway, Veritas, RACS, workflow/runtime components, adapters, packs, distribution and validation.

The `packages/` directory remains the curated package and contract distribution surface. It is not the complete description of what exists in the repository.

Open execution has a hard operational invariant:

`NO_MANDATORY_PHONE_HOME`

A local installation must be able to authorize, deny, escalate, enforce, replay and produce evidence without contacting Heimel, a license server or a Heimel-hosted service.

This includes the ability to demonstrate authority revocation and a fresh consequence-time check locally.

## Enterprise governance boundary

Heimel Enterprise is organization-level governance infrastructure around the open execution mechanism.

It may own:

- identity federation, SSO, SCIM and IAM integration
- authority administration and delegated administration
- separation of duties and approval flows
- policy lifecycle, versioning and rollback
- organization and tenant boundaries
- secrets management
- deployment governance
- high availability and disaster recovery
- evidence retention operations
- observability, SLA and support

Enterprise must remain separable from the local governed-execution mechanism. It must not be implemented as a commercial entitlement required to use the local consequence path.

```text
Heimel Open       → governed-execution mechanism
Heimel Enterprise → organization-level governance/control plane
Heimel Gateway    → exclusive consequence enforcement
Veritas           → effect/outcome evidence
Heimel Certified  → official conformance attestation
```

Managed deployment forms — Cloud, Private Cloud, Sovereign and Air-gapped — must preserve the same governance semantics.

The canonical machine-readable boundary is `docs/open-enterprise-contract.yaml`.

## Conformance and certification

The conformance suite is open.

Official Heimel certification is a separate trust service. A certification claim must be bound to an implementation identity, conformance-suite version, tested profile, result, issuance time and validity.

Passing the open conformance suite does not by itself create an official Heimel certification claim.

## Governed-consequence metering

The canonical commercial metering concept is `governed_consequence_event`, not human seat count.

A governed consequence event binds an exact effect identity to the consequence-path decision, enforcement state and recorded outcome/evidence state.

A denied attempt is not equivalent to a successfully executed consequence. Commercial contracts may meter decision events separately, but that must be explicit.

## Boundary invariants

1. **No direct effect path.** Consequence-bearing actions pass through the governed boundary.
2. **Fresh authority.** The exact effect is authorized against current operative state at consequence time.
3. **Exact binding.** Decision, effect, permit and receipt remain deterministically correlated.
4. **Fail closed.** Missing, stale or mismatched material authority, state, evidence or binding cannot silently execute.
5. **Evidence by construction.** Effects and outcomes remain attributable and replayable.
6. **State requires admission.** A receipt or provider response cannot directly mint operative state.
7. **Model independence.** Models, workers and orchestration may change without moving the consequence boundary.
8. **No mandatory phone-home.** Local governed execution must remain operational without a commercial entitlement or Heimel-hosted dependency.

## Licensing boundary

The repository default is Apache-2.0 unless a component explicitly states otherwise.

Open standards, contracts, schemas, SDKs, conformance material and local governed-execution surfaces must remain genuinely open source if described as open source.

Enterprise functionality is separate software or service. Source-available or commercially restricted code must not be described as open source.

## Remaining release gate

One material public-release gap remains: a coherent, documented end-to-end install and execution path proving the complete local consequence path from proposed effect through fresh authorization, enforcement, receipt and replay.

Repository visibility is an operational publication setting, not an architecture property; the repository must be made public before claiming the public release is complete.
