# Headless Workflow Harness

Status: approved Factory OS architecture

## Decision

VALO Factory adopts a provider-neutral, headless harness pattern for durable workflows.

The model is not the workflow. A workflow is a canonical Factory primitive that names capabilities and ordered steps. Provider/model selection and user-interface surface are bound only when the workflow is invoked.

This pattern is externally validated by systems such as Ori, which separates the durable harness from the underlying model and exposes domain workflows as callable primitives. VALO adopts the pattern, not an Ori runtime dependency.

Source pattern: https://www.linkedin.com/posts/introducing-ori-harness-your-favorite-harness-ugcPost-7490474154790428672-1ue0/

## Canonical flow

```text
CLI / MCP / API / Workbench / Voice / other surface
                    |
                    v
          Headless Workflow Harness
                    |
          Canonical Workflow Primitive
                    |
       provider selected per invocation
                    |
      provider entitlement/auth adapter
                    |
      context / memory / sandbox harness
                    |
                 VAIG
                    |
                 REHT
                    |
                 RACS
                    |
            execution surface
                    |
                Veritas
```

## Workflow primitive contract

A workflow primitive is versioned and provider-neutral. It contains:

- `primitive_id` and integer `version`
- description
- ordered workflow steps
- capability required by each step
- whether a step is consequence-bearing
- required aggregate capabilities
- `authority_effect = none`

A primitive MUST NOT contain:

- model identity
- provider identity
- provider credentials or entitlement state
- UI/surface-specific behavior
- authorization decisions or permits

The canonical wire contract is `schemas/workflow-primitive.schema.json`.

## Consequence boundary

Advisory/read-only steps carry no authority path.

A consequence-bearing step must declare exactly:

```text
VAIG -> REHT -> RACS
```

This declaration is a dependency on the governance path, not an authorization result. The workflow harness cannot create, infer, cache or reuse execution authority.

REHT remains the authorization boundary. RACS expresses the decision. Veritas records the resulting execution/evidence receipt chain.

## Headless invocation

`HeadlessWorkflowHarness` binds a registered primitive to invocation-time context:

- run
- actor
- surface
- selected supported provider
- optional context reference
- deterministic input digest
- primitive digest

The same primitive can therefore be invoked from CLI, MCP, API, Workbench, voice or another surface without forking workflow semantics.

Surface identity is metadata. It does not change the primitive contract.

## Provider neutrality

Provider selection occurs when a workflow is invoked, never when it is defined.

The current provider IDs are owned by `lib/provider_entitlements.py`. This allows the same workflow definition to run through officially supported Codex, Claude Code, Antigravity or GitHub Copilot entitlement paths without changing the workflow itself.

A provider entitlement proves an available supported execution capability. It does not grant VALO authority.

## Relationship to the long-horizon harness

`lib/long_horizon.py` owns resumability, child contexts, memory compaction, sandbox lifecycle and judge-fork review.

`lib/workflow_harness.py` owns reusable workflow definitions and headless invocation planning.

They are complementary orchestration components and share the same hard boundary: neither has an authority or execution surface.

## Factory pattern

The intended composition is:

```text
orchestrator
  -> canonical workflow primitive
  -> discovery capability
  -> execution capability
  -> independent judgment capability
  -> governed consequence boundary where required
  -> evidence/receipt output
```

Concrete workflows may compose these capabilities differently. The contract prevents a workflow from becoming coupled to one provider, one model or one UI.

## Non-goals

This change does not:

- add a new authority layer
- move authorization into the orchestrator
- replace VAIG, REHT, RACS or Veritas
- execute provider OAuth flows
- embed provider secrets
- require Ori or any external harness runtime
- make workflow state equivalent to permission
