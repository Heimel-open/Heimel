# Governance Execution Architecture (GEA)

Date: 2026-07-11
Status: current active architecture
Ownership: VALO Research Group AS / Njål Gaute Solland

## Purpose

GEA is the VALO-owned reference architecture for governing the path from observed reality to real-world execution.

It does not depend on MECHA, EFA, Charles Rupp, or any other collaboration-specific framework.

Earlier documents may contain historical collaboration references. Those references are preserved as provenance but are not part of the active GEA definition.

## Core principle

```text
Ability is not authority.
Authorization is not sufficient.
Admissibility must remain valid until execution completes.
```

## Active architecture

```text
Reality
  ↓
Speider
  Collection, connectors, provenance and normalization
  ↓
BARO
  Observation analysis, correlation and Reality Packages
  ↓
VAIG
  Runtime governance evaluation, uncertainty, risk and policy checks
  ↓
REHT
  Action admissibility: is this action right to execute now?
  ↓
RACS
  Action, authority, evidence, state and receipt contracts
  ↓
VALO Core
  Deterministic state transitions and enforcement
  ↓
Execution
  ↓
Outcome and immutable receipt
```

## GEA responsibilities

GEA defines:

- governance boundaries
- authority inputs
- evidence requirements
- policy evaluation points
- state admissibility
- continuous integrity
- escalation and human decision points
- execution clearance
- outcome capture
- receipt and audit requirements

GEA does not claim ownership of generic concepts such as authorization, policy, identity, evidence, audit or human oversight.

The VALO contribution is the integrated architecture, object boundaries, state relationships and execution path expressed in this repository family.

## Human authority

Human and organizational authority enter GEA as explicit governed inputs.

GEA does not require a named external framework to represent authority. Implementations may integrate corporate delegation systems, boards, operators, regulated approval processes or other lawful authority structures.

## Component boundaries

### Speider

Collects and normalizes source material. It does not interpret governance legitimacy.

### BARO

Analyzes observable signals and produces structured evidence packages. It does not authorize action.

### VAIG

Evaluates runtime risk, policy, uncertainty, evidence quality and operational conditions. It does not execute business effects.

### REHT

Determines whether the proposed action is admissible in the current authority, context, policy, evidence and state.

### RACS

Defines interoperable action-control contracts and receipts. It does not make decisions.

### VALO Core

Enforces deterministic execution-state transitions. It does not determine morality, truth or organizational legitimacy.

## Decision surface

The active runtime decision set is:

- ALLOW
- MODIFY
- DEFER
- DENY
- STEP_UP
- HALT

## Continuous integrity

Admissibility is not a one-time gate.

A previously allowed action must be halted, deferred or escalated if authority, policy, evidence, context, risk or system state changes materially during execution.

## Provenance rule

Any future external framework or collaborator contribution must be recorded with:

- source
- author
- date
- license or permission
- exact dependency
- whether the dependency is normative or informative

Absence of such a record means the external concept must not be represented as a native GEA dependency.
