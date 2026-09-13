# L4 Applications Layer

Status: draft v1.0
Scope: application layer specification
Boundary: applications consume governed execution; they must not bypass ACS, VAIG or Phi for governed actions

## Purpose

L4 delivers product and workflow value using the governed execution stack.

## Examples

- BARO
- REHT
- Pilot
- Scout
- AI Consultant
- enterprise workflows
- future domain systems

## Responsibilities

Applications may:

- collect user intent
- render UI
- call ACS-compatible endpoints
- display decisions and receipts
- handle domain workflows
- integrate with enterprise systems

## Prohibited responsibility

Applications must not independently decide governed execution when the action is within ACS/VAIG/Phi scope.

Applications must not bypass:

- ACS packet semantics
- VAIG environment construction
- Phi transition admission
- receipt generation

## Relationship to ACS

Applications communicate through ACS.

## Relationship to VAIG

Applications rely on VAIG to construct the execution context.

## Relationship to Phi Runtime

Applications should not call Phi directly unless explicitly acting as a certified ACS/VAIG adapter.

## Contract

```text
L4 consumes governed execution.
L4 does not define the execution boundary.
```
