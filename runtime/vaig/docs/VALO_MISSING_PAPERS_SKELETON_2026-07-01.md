# VALO Missing Papers Skeleton

Date: 2026-07-01
Status: repository research planning skeleton
Scope: VALO / GEA / VAIG / TAD / tau / PERT

This note does not replace `SYSTEM_MAP.md`.

## Purpose

This file lists the missing papers needed to turn VALO 2.1 / 2.2 from architecture into a defensible research package.

It separates:

- external literature
- VALO architecture synthesis
- original VALO contributions
- validation still required

## 1. Governance Execution Architecture

Working title:

Governance Execution Architecture: A Reference Stack for Runtime Control of Agentic AI Systems

Core claim:

Runtime AI governance requires a complete execution stack, not isolated guardrails.

Sections:

1. Ability is not authority
2. Related work
3. Architecture: ELSA, MECHA, RUPP, IGL, VAIG, SOL, ACT, PERT, NJAL
4. Open adapter model
5. ACS as contract
6. Limitations
7. Future work

Original contribution:

GEA as integrated reference architecture.

## 2. State Admissibility

Working title:

State Admissibility: Validity of Reality as a Precondition for Autonomous Execution

Core claim:

Identity and authorization are insufficient. The current system state must also justify action.

Sections:

1. Problem
2. Definition
3. State, evidence, authority, policy and context
4. Decision states: allow, pause, block, escalate
5. Runtime placement inside VAIG
6. Testable propositions

Original contribution:

State admissibility as a distinct execution precondition.

## 3. Temporal Admissibility Distortion / TAD

Working title:

Temporal Admissibility Distortion: Rate Mismatch and Freshness Failure in Distributed AI Governance

Core claim:

A governance decision may be valid when issued but invalid when executed.

Sections:

1. Problem: action rate exceeds governance rate
2. Definition of TAD
3. Metrics: exposure X, rate separation R, freshness margin F
4. Failure modes: stale approval, partial pause, oversight aliasing
5. Controls: validity horizon, local pause/block, causal receipts
6. VAIG integration
7. Testable propositions

Original contribution:

Temporal validity as a measurable admissibility condition.

## 4. Continuous Integrity

Working title:

Continuous Integrity: Runtime Legitimacy Preservation Across Autonomous Action Chains

Core claim:

Governance must preserve legitimacy throughout execution, not only before execution starts.

Sections:

1. Long action chains and legitimacy drift
2. Definition
3. Difference from monitoring and logging
4. Runtime loop: observe, validate, continue, pause, halt
5. Relation to State Admissibility and TAD
6. Integrity preservation theorem
7. Tests and invariants

Original contribution:

Continuous Integrity as the condition that keeps authorization live.

## 5. tau Structural Coherence Diagnostics

Working title:

Spectral Coherence Diagnostics for Runtime AI Governance

Core claim:

Structural coherence can be used as a governance signal.

Sections:

1. Spectral entropy and effective rank
2. tau definition
3. Empirical pattern: coherent > random > repetitive
4. tau as sensor, not judge
5. VAIG integration
6. Failure modes: replay, collapse, unstable diffusion
7. Limits
8. Future validation

Original contribution:

Using tau as a runtime diagnostic inside governance.

## 6. PERT Closed Governance Loop

Working title:

Post-Execution Reconciliation and Policy Tuning: Closing the Governance Loop for Agentic AI

Core claim:

Pre-execution authorization must be followed by post-execution reconciliation.

Sections:

1. Authorization does not prove outcome alignment
2. PERT definition
3. Intent, boundary, expected effect, actual outcome
4. Harmony and anomaly states
5. Policy feedback and boundary tuning
6. Relation to NIST AI RMF and ISO/IEC 42001 monitoring
7. Receipt and proof requirements
8. Prototype plan

Original contribution:

PERT as post-execution reconciliation and feedback layer.

## 7. ACS / VACS Open Adapter Standard

Working title:

Agent Control Standard: An Open Action Envelope for Governed AI Execution

Core claim:

Governance components should be replaceable if they implement a common action-control envelope.

Sections:

1. Fragmented agent tools
2. ACS packet
3. Authority, identity, evidence, policy, context, decision, receipt
4. VACS as VALO profile
5. Adapter model
6. Example packets
7. Compatibility tests
8. Open standard roadmap

Original contribution:

ACS as action-control packet; VACS as VALO profile.

## 8. NJAL Proof and Accountability

Working title:

NJAL: Non-Repudiation, Jurisdictional Accountability and Legal Proof for Agentic AI Execution

Core claim:

Agentic AI needs runtime proof of action, authority, jurisdiction and accountability.

Sections:

1. AI action without accountable proof
2. NJAL definition
3. Receipt model
4. Jurisdictional metadata
5. Non-repudiation requirements
6. Integration with ACS, VAIG and PERT
7. Audit use cases
8. Limits and open questions

Original contribution:

NJAL as proof and accountability layer for governed execution.

## 9. BARO as Evidence Feed

Working title:

BARO: Observation Without Authority in Governance Execution Architectures

Core claim:

Observation should feed governance without becoming governance.

Sections:

1. Monitoring versus decision authority
2. BARO definition
3. Evidence feeds
4. Risk and pressure signals
5. Mapping into ACS evidence fields
6. Boundary: BARO observes, VAIG decides
7. Examples
8. Roadmap

Original contribution:

BARO as sensor layer, not decision layer.

## Priority order

1. GEA reference architecture
2. State Admissibility
3. TAD
4. Continuous Integrity
5. PERT
6. ACS / VACS
7. tau diagnostics
8. NJAL
9. BARO

Reason:

The architecture must be established before the individual modules are defended.
