# VAIG Execution Boundary

Status: current architecture  
Scope: runtime governance around agent and tool execution  
IP classification: `solland_valo_owned_contribution`

VAIG must not be implemented as a single output filter.

It operates as an execution boundary around the agent loop.

## Hard boundary

VAIG evaluates bounded transitions from represented evidence and context toward intent, tool use, execution, refusal, escalation and receipt-linked accountability.

VAIG does not:

- determine truth itself
- grant human or organizational authority
- create legal standing
- replace accountable operators
- own general morality or social legitimacy
- act as the final deterministic state-transition enforcer

Human and organizational authority enter VAIG as explicit, externally governed inputs. REHT evaluates whether the proposed action is admissible. VALO Core enforces the resulting permitted state transition. RACS carries the action and receipt contract.

## Core position

Technical refusal does not remove uncertainty. It transfers remaining uncertainty into an accountable review or recovery path.

The measurable question is whether the system preserves a usable chain after that transfer:

- why the boundary refused or escalated
- what uncertainty remains
- what authority is required
- who or which role may act next
- which recovery paths remain permitted
- how accountability continues
- which receipt preserves the event

VAIG owns the runtime evaluation record, uncertainty inventory, decision recommendation and audit evidence. Authority remains external. Admissibility belongs to REHT. Enforcement belongs to VALO Core.

## Placement in the agent loop

VAIG should evaluate both before and after model generation and around intermediate tool calls.

### Pre-gate evaluation

- requested outcome
- task risk class
- available authority evidence
- allowed tools
- data-access scope
- policy and contextual constraints
- whether human review is required before consequence

This prevents an inadmissible execution path from forming unchecked.

### Post-generation evaluation

- policy consistency
- uncertainty visibility
- claim substantiation requirements
- semantic and contextual drift
- potential consequence
- escalation requirements
- receipt requirements

### Agentic execution chain

```text
Input
-> VAIG pre-evaluation
-> plan
-> VAIG step evaluation
-> tool candidate
-> REHT admissibility
-> Core enforcement
-> observation
-> VAIG re-evaluation
-> next candidate
-> receipt
```

Serious failures often occur inside intermediate execution chains rather than only in the initial prompt or final response.

A tool observation may preserve a false assumption, amplify it in the next step, or change the state on which the previous clearance depended. Continuous Integrity therefore requires re-evaluation at meaningful boundary crossings.

## Dynamic boundary depth

Applying the same verification cost to every step creates unnecessary latency. Removing the boundary creates unmanaged risk.

VAIG uses risk-adaptive evaluation depth.

### Fast path

Suitable for low-risk, reversible observations:

- read-only retrieval
- parsing
- schema validation
- harmless transformation
- local observation

Typical checks:

- schema conformance
- allowed-tool list
- state-transition shape
- hash-chain continuity
- basic policy constraints
- source provenance presence

### Review path

Suitable for interpretation or moderate uncertainty:

- semantic consistency
- competing hypotheses
- missing evidence
- normative or contextual drift
- possible escalation
- human confirmation where policy requires it

### Hard path

Required for consequential actions:

- sending external messages
- writing or deleting files
- changing records or permissions
- executing code
- financial operations
- legal, medical, safety or compliance-sensitive outputs
- production changes
- external tool calls with irreversible or material effect

Typical checks:

- authority evidence
- policy and risk constraints
- evidence sufficiency
- current state admissibility
- reversibility and rollback
- human approval where required
- complete receipt policy

## Latency principle

Each boundary crossing should be classified by:

- reversibility
- external consequence
- uncertainty
- tool authority
- domain risk
- evidence quality
- accumulated drift
- current governance state

A reversible read-only observation may use a deterministic fast path. An irreversible or high-consequence action enters the hard path.

## Drift accumulation

A single low-risk step may be safe while a chain of individually low-risk steps becomes unsafe.

VAIG tracks bounded cumulative drift across:

```text
original request
-> governed context
-> plan
-> tool result
-> interpretation
-> next action candidate
```

When drift exceeds the configured threshold, the system must not continue automatically. It should re-ground, request clarification, enter review, defer or halt according to the active policy and REHT outcome.

## Continuous Integrity

A clearance is not permanent merely because it was valid at an earlier step.

VAIG must re-evaluate when any material input changes, including:

- authority scope
- policy version
- evidence freshness
- target resource
- tool or connector state
- external environment
- accumulated risk
- human approval validity
- execution timing

The governing question is not only whether the action was valid when proposed, but whether it remains valid at the point of consequence.

## Active component boundary

```text
VALO Harness orchestrates.
VAIG evaluates runtime evidence, risk and policy conditions.
REHT determines admissibility.
VALO Core enforces deterministic state transitions.
RACS carries contracts and receipts.
External human and organizational systems own authority and accountability.
```

Historical documents may refer to MECHA, EFA, ACS, VACS, Phi Runtime, IGL, WHY Gate or other collaboration-era constructs. Those references are not active dependencies unless explicitly reintroduced with documented origin, permission and implementation.

## Relation to semantic and coherence research

Active Inference, semantic models, coherence criteria and other research can inform observation or evaluation.

They must not be collapsed into the execution-governance layer without bounded definitions, testable properties and explicit provenance.

A robust architecture separates:

- observation
- semantic interpretation
- runtime governance evaluation
- admissibility
- deterministic enforcement
- organizational authority

## Architectural principle

VAIG is not merely a refusal mechanism.

VAIG is a runtime governance system that:

- evaluates risk before consequence
- controls tool exposure through governed context
- re-evaluates intermediate steps
- surfaces uncertainty
- links decisions to evidence
- adapts evaluation depth to risk and reversibility
- transfers unresolved cases to accountable review paths
- records the full evaluation chain

## Summary

For a simple model call:

```text
Input -> VAIG -> Model -> VAIG -> REHT -> Core -> Output / Action -> Receipt
```

For agentic systems:

```text
Input
-> Harness
-> VAIG
-> plan
-> VAIG
-> tool candidate
-> REHT
-> Core
-> observation
-> VAIG
-> next candidate
-> receipt
```

VAIG is an execution boundary around the agent loop, not a filter at the end. It is risk-adaptive, model-independent and continuously sensitive to changing state.