# Sim as a capability route under VALO

Status: research/adoption note
External reference: https://github.com/simstudioai/sim

## Decision

Adopt the useful execution-architecture patterns demonstrated by Sim, but do not adopt Sim's runtime as an authority system and do not make it a Kernel dependency.

Sim is treated as a capability composition and execution surface. VALO remains the authority, admissibility, consequence-time decision and evidence boundary.

Canonical relationship:

```text
intent
  -> capability composition / workflow runtime
  -> exact effect request
  -> governed workspace conformance
  -> sealed execution binding
  -> REHT fresh authority resolution
  -> RACS ALLOW | DENY | ESCALATE
  -> Gateway bounded execution
  -> external effect
  -> Veritas receipt
  -> BARO verification
  -> Kernel event
```

A workflow runtime may decide how to route work. It may not decide whether the resulting consequence is authorized.

## What is worth adopting

Sim's executor has a clear separation between workflow representation and execution. Its handler registry centralizes execution of agent, API, function, condition, router, human-in-the-loop, evaluator, credential, workflow and generic blocks. This is a useful capability-route pattern because heterogeneous execution surfaces converge through a small number of runtime boundaries.

Its generic execution path also preserves execution context such as workflow, workspace, execution, user, block and invocation identity before calling the selected tool. Invocation identity is designed to remain stable across retries while remaining distinct across loop iterations and parallel branches. That is a useful provenance and idempotency pattern.

Sim additionally tracks resolved-secret provenance and projects secret-bearing inputs at model/external boundaries. The generalizable lesson is not secret handling itself but boundary-aware provenance: values should carry provenance across transformation without granting the receiving runtime authority over their meaning.

Adopt these patterns:

- centralized capability handler/registry
- explicit workflow-to-execution boundary
- stable per-invocation identity across retries
- distinct invocation identity across parallel/iterated effects
- boundary-aware provenance and input projection
- isolated execution as a replaceable execution mechanism
- runtime logs as evidence-producing observations
- credentials as execution prerequisites, never authority

## What VALO adds

A capability route is not handlingsrett.

Possession of all of the following is still insufficient to authorize an effect:

- a valid workflow
- a valid model output
- a valid connector
- valid credentials
- a human approval block
- a successful evaluator result
- a routable API call
- a stable invocation id

The consequence-bearing action must still be bound to current authoritative state and evaluated at consequence time.

The mandatory VALO insertion point is immediately before the first operation that can cause an external effect.

```text
runtime handler
  -> capability resolved
  -> candidate effect envelope
  -> VALO consequence boundary
       -> current state root
       -> current identity
       -> current authority/delegation
       -> current constraints
       -> exact action binding
       -> REHT/RACS
  -> only on ALLOW: external tool/provider invocation
```

There is no permitted fallback path from a handler directly to a consequence-bearing tool.

## Effect envelope

A runtime adapter should project a provider-neutral effect envelope before external execution. It should contain references/digests rather than duplicate authority semantics owned by Kernel.

Minimum conceptual fields:

```text
runtime_id
workflow_id
runtime_execution_id
runtime_invocation_id
principal_id
workspace_id
capability_id
candidate_action_digest
credential_ref
provider_ref
input_provenance_refs
requested_at
```

These fields describe the proposed execution. They do not authorize it.

The adapter then binds the candidate effect to the existing VALO sealed execution contract. REHT resolves authority fresh. RACS decides. Gateway enforces only the bounded allowed action.

## Stale-authority demonstrator

Use the same workflow and runtime in both paths.

Initial state:

```text
08:00 principal mandate permits payment <= 50,000
08:30 workflow is composed/approved
09:00 mandate changes to <= 25,000
09:05 existing workflow attempts payment = 45,000
```

Vanilla workflow-runtime question:

```text
Can the configured tool execute with the available credential and inputs?
```

VALO question:

```text
Does this exact principal still have authority for this exact effect now?
```

Required VALO result:

```text
REHT fresh state -> stale earlier approval is non-operative
RACS -> DENY or ESCALATE
Gateway -> no invocation
external effect -> null
receipt -> denied/blocked attempt with authority/state bindings
```

The demonstrator is intentionally runtime-independent. Sim is a strong reference surface because its generic handler centralizes many external tool invocations, but the same adapter contract applies to any workflow/runtime system.

## Security property

`NO_DIRECT_EFFECT_PATH` becomes a runtime-integration requirement:

For every consequence-bearing capability route, removing or bypassing the VALO consequence boundary must make external execution impossible, not merely unlogged or non-compliant.

Therefore an integration that adds REHT/RACS as an optional workflow block is insufficient. A user could route around it. The boundary must sit below workflow composition, at or immediately before the actual effect executor/Gateway.

Human-in-the-loop is similarly subordinate. Human approval is evidence or an authority-relevant event when the governing contract says it is, but a HITL node is not itself universal authority to act.

## Provenance mapping

Preserve runtime execution identity rather than replacing it:

```text
VALO execution identity
  -> authoritative execution binding

runtime execution identity
  -> provenance of how the capability route realized the binding

provider idempotency identity
  -> provider-side duplicate-effect control
```

These identities should be linked but never collapsed. Provider or runtime identities cannot widen the authorized action.

## Adapter rule

Named runtimes are adapters, not constitutional dependencies.

A Sim adapter may translate Sim execution context and tool invocation metadata into the provider-neutral VALO effect envelope. The Kernel, REHT/RACS semantics, Gateway enforcement and evidence contracts must remain testable with no Sim installation and no Sim-specific types.

## Research conclusion

Sim reinforces the architectural split:

```text
model = capability generator
workflow/runtime = capability route
credentials/provider = effect mechanism
VALO = handlingsrett boundary
```

The runtime answers how a capability can be realized.

VALO answers whether that realization is permitted to become consequential now.
