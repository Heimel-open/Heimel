# Shapes PeopleOS adoption into AI Work OS

Issue: `nsolland/valo-operator#2`  
Date: 2026-08-08  
Status: adopted pattern / implementation target

Sources:
- https://shapes.co/lp/ai-hr-platform
- https://shapes.co/
- https://mcp.shapes.co/

## Decision

Adopt the useful Shapes product pattern into the AI Work OS: one connected people/work context, agents that carry routine administration, natural-language generated operational views/tools, and permission-aware AI access to workforce context.

Do not copy Shapes' product architecture, create a parallel authorization layer, or turn `valo-operator` into an HRIS.

The Operator remains a thin, generic execution surface. People-specific state, transitions and admissibility belong in a replaceable PeopleOps domain pack. Provider-specific HR systems remain upstream context sources or downstream execution targets.

## What is adopted

### 1. PeopleOps becomes a first-class Work OS domain

The Work OS should be able to expose, through the same Operator surface used by other domains:

- people directory and organizational structure;
- manager/reporting relationships;
- joiner / mover / leaver processes;
- onboarding and offboarding;
- time-away and attendance workflow state;
- performance-cycle administration;
- policies, handbooks and employee help content;
- document and e-sign workflow initiation;
- compensation, promotion and role-change workflow preparation;
- workforce analytics and operational dashboards.

This is a domain surface, not a new platform layer.

### 2. Agents that act, but only through registered Functions

Shapes demonstrates the useful product expectation that agents should carry processes end-to-end rather than merely answer questions.

VALO adopts the product expectation, but the execution rule is stricter:

```text
human intent / trigger
  -> agent
  -> current people + organization context
  -> read-only view OR candidate operation
  -> registered Function
  -> Function Fabric compile
  -> Workflow ISA
  -> domain-pack pre-execution admissibility
  -> fresh execution context
  -> REHT
  -> Gateway
  -> Veritas
  -> BARO
  -> Kernel
```

An agent may prepare, coordinate, calculate, route and propose. It cannot gain authority from workflow ownership, source-system permissions, model confidence, generated code or agent role.

### 3. Natural-language generated views and tools

Adopt the Shapes/Vibe pattern: a user can describe the operational view or tool they need in plain language.

Compilation target:

- read-only request -> deterministic Operator view/query contract;
- effectful request -> a bounded, versioned Function definition before execution.

A generated effectful tool must declare at least:

- owner;
- purpose;
- typed inputs/outputs;
- source and target scopes;
- effect type;
- risk class;
- authority requirement;
- postconditions;
- idempotency policy;
- evidence requirements.

Generation never creates authority. The caller cannot override the registered Function's effect, risk, authority, postconditions or idempotency at runtime.

### 4. Permission-aware workforce context connector

Shapes MCP demonstrates a useful boundary for external AI access: authenticated user permissions carry into the connector and the current MCP surface is read-only.

Adopt this as the default provider pattern:

```text
HRIS / PeopleOS / directory
  -> authenticated, scoped read connector
  -> provenance-bound context
  -> Operator / pack evaluation input
```

Useful context includes:

- stable person/agent identity reference;
- employment/engagement state;
- role, level, team and manager relationships;
- location/jurisdiction;
- approved organizational scope;
- workflow state;
- policy/document references;
- source timestamp, version and provenance.

Source permissions bound what context can be read. They do not authorize a downstream consequential action.

### 5. HR provider writes are execution targets

If Shapes, Rippling, Deel or another provider exposes write APIs, those APIs are downstream targets behind the normal Operator chain.

Examples of consequential PeopleOps effects:

- compensation change;
- promotion or role change;
- employment-status change;
- offboarding commit;
- payroll-impacting mutation;
- access revocation caused by workforce state;
- e-sign or contract action;
- external employee communication carrying material effect.

These must be registered Functions and receive fresh REHT clearance for the exact action.

## Domain-pack placement

Implementation target: a replaceable `PeopleOps Pack` following the same architectural rule as existing domain packs.

The pack owns only domain semantics such as:

- allowed people-process state transitions;
- domain-specific pre-execution admissibility;
- typed Function definitions;
- people-domain postconditions;
- domain projections required by Operator views.

It does not own authorization. REHT remains the sole authorization boundary.

The Operator should require no HR-specific authorization logic.

## Provider adapter placement

Provider differences remain configuration/adapter concerns, consistent with the existing vendor-neutral Operator rule.

A Shapes adapter, Rippling adapter or other HR connector may normalize:

- authentication;
- paths and payload fields;
- stable identifiers;
- read-context schema;
- write payload mapping;
- idempotency mechanism;
- observed-state endpoint and success-state mapping.

No adapter may decide whether the action is allowed.

## People analytics boundary

Adopt useful organization-level analytics and dashboards without making individual prediction an execution authority source.

Analytics may identify patterns, surface conditions and recommend attention. They remain evidence/advisory input.

A risk score, flight-risk prediction, performance score or similar inference must never directly trigger an adverse employment action.

## Required negative proofs

The PeopleOps implementation is not complete until deterministic tests prove:

1. valid source-system access does not authorize a compensation or employment change;
2. a natural-language generated tool cannot downgrade its registered effect/risk/authority contract at invocation time;
3. changed person, amount, target, role, payload or context invalidates stale clearance;
4. revoked/stale employment or delegation context forces re-evaluation;
5. read-only provider credentials cannot perform writes;
6. provider HTTP success without observed desired state is not an EffectVerified success;
7. retry does not duplicate a consequential PeopleOps effect;
8. an analytics score alone cannot commit an adverse worker action;
9. DENY produces zero external effect;
10. the same Operator API can drive a PeopleOps pack without changing REHT, Workflow ISA, Function Fabric or Kernel.

## Canonical invariant

```text
PeopleOS context tells VALO what is true about the organization.
The PeopleOps pack tells VALO what domain transition is valid.
REHT decides whether this exact consequential action may happen now.
Operator never invents authority.
```
