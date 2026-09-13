# L3 ACS Protocol Layer

Status: draft v1.0
Scope: open execution-governance protocol layer
Boundary: ACS standardizes communication; it is not a model or runtime implementation

## Purpose

ACS provides an interoperable protocol for governed AI execution.

It allows independent systems to exchange requests, authority, evidence, environments, decisions and receipts.

## Objects

ACS standardizes:

- request
- intent
- authority
- evidence
- environment
- risk contract
- decision
- receipt
- result

## Relationship to VAIG

VAIG may implement an ACS-compatible governance runtime.

ACS defines the packet and receipt semantics used across implementations.

## Relationship to Phi Runtime

Phi Runtime is the normative execution model for ACS-governed transition admission.

ACS carries the decision and receipt.

Phi produces the decision and receipt.

## Interoperability requirement

Independent implementations should be able to exchange ACS packets without sharing the same model, application or runtime internals.

## Contract

```text
ACS standardizes execution-governance communication.
ACS does not itself perform inference or mathematical admission checks.
```
