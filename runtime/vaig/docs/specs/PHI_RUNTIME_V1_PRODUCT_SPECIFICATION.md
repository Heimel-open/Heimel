# Phi Runtime v1.0 Product Specification

Status: draft v1.0
Scope: normative product specification
Boundary: does not expand VAIG Core beyond SYSTEM_MAP.md

Phi Runtime is a deterministic execution-boundary runtime.

It is independent of any LLM, agent, workflow engine or application.

Its only responsibility is to determine whether a proposed state transition preserves system integrity.

## 1. Product definition

Phi Runtime separates reasoning from execution.

```text
Reasoning proposes.
Phi authorizes.
VAIG governs context.
ACS communicates decisions.
```

Phi Runtime is not a model, guardrail prompt, policy classifier or application.

It is the runtime that enforces admissible state transitions.

## 2. Layer placement

```text
L4 Applications
L3 ACS Protocol
L2 VAIG Runtime
L1 Phi Runtime
L0 Inference Engine
```

## 3. L0 - Inference

Mission: produce candidate transitions.

Input:

- current state
- prompt or task
- available tools

Output:

- candidate output
- candidate action
- candidate tool call
- candidate plan

Contract:

- no governance
- no authorization
- no final execution authority

## 4. L1 - Phi Runtime

Mission: determine whether a candidate transition is admissible.

Pipeline:

```text
Candidate
-> Projection
-> Integrity Functional
-> Dynamic Lambda
-> Phi Decision
-> Receipt
-> Commit
```

L1 is deterministic. It must not call a secondary LLM to decide admissibility.

## 5. State projection

Operator:

```text
P: O -> X
```

Where:

- O is raw output: text, JSON, tool call, plan or action packet
- X is the operational state vector

Operational state vector:

```text
x = [
  semantic_state,
  policy_state,
  authority_state,
  trust_state,
  context_state,
  tool_state,
  evidence_state,
  provenance_state,
  receipt_state
]
```

Requirements:

- deterministic
- reproducible
- idempotent
- replayable

## 6. Integrity functional

Operator:

```text
F_free(x, e)
```

Definition:

```text
F_free(x, e) =
  w1 * d_M(x, K(e))^2
  + w2 * Delta(x_t, x)^2
  + w3 * B(x, e)
  + w4 * C(x, e)
```

Components:

- geometric distance to admissible state region
- transition energy
- barrier potential
- deterministic constraint violations

Output:

- one scalar free-energy value

## 7. Dynamic lambda

Operator:

```text
lambda(e)
```

Purpose: define the current membrane permeability.

Inputs:

- trust
- authority
- isolation
- domain
- criticality
- mode

Canonical form:

```text
lambda(e) =
  lambda_base
  * trust_multiplier(e)
  * authority_multiplier(e)
  * isolation_multiplier(e)
  * domain_multiplier(e)
  - criticality_penalty(e)
```

Modes:

- NORMAL: ordinary admissible operation
- SAFE: reduced permeability
- CRITICAL: near-zero permeability
- HALT: no transition permitted

## 8. Phi decision operator

Rule:

```text
ALLOW iff F_free(x_next, e_next) <= lambda(e_next)
```

Outputs:

- ALLOW
- BLOCK
- DEFER
- HALT

Decision semantics:

- ALLOW: commit candidate state
- BLOCK: do not commit candidate state
- DEFER: preserve state and route to higher authority or RRP
- HALT: preserve state and stop execution path

## 9. Receipt

Every decision must produce a receipt.

Minimum fields:

- sequence number
- runtime id
- state hash
- candidate hash
- environment hash
- authority hash
- policy hash
- decision
- free-energy summary or hash
- lambda summary or hash
- previous receipt hash
- receipt hash
- signature or signing placeholder

Receipts form a hash chain.

The receipt chain proves decision-path continuity. It does not by itself prove that the integrity functional was correctly specified.

## 10. Commit rule

Only ALLOW updates runtime state.

All other decisions preserve the previous valid state.

```text
ALLOW -> x_t := x_next
BLOCK -> x_t unchanged
DEFER -> x_t unchanged
HALT -> x_t unchanged
```

This is the operational invariant.

## 11. L2 - VAIG Runtime

Mission: construct the execution environment.

VAIG supplies:

- authority
- evidence
- policy
- risk
- trust
- criticality
- receipt policy
- RRP handoff

Output:

```text
e
```

VAIG defines context. Phi evaluates transition admissibility.

## 12. L3 - ACS Protocol

Mission: standardize communication.

Objects:

- request
- authority
- evidence
- environment
- receipt
- decision
- result

ACS is implementation-independent.

## 13. L4 - Applications

Examples:

- BARO
- Scout
- Pilot
- REHT
- AI Consultant
- enterprise workflows

Applications should not bypass ACS/VAIG/Phi for governed execution.

## 14. Mathematical foundation

Phi Runtime v1.0 depends on Execution Boundary Mathematics:

- Integrity Preservation Theorem
- State Projection Operator
- Integrity Functional
- Dynamic Lambda
- Decision Operator
- Receipt Invariant
- Viability Condition

## 15. Runtime guarantees

Phi Runtime guarantees only:

- deterministic decisions under identical inputs
- replayable execution
- receipt continuity
- no committed transition outside the specified admissible region
- previous valid state is preserved on BLOCK, DEFER and HALT

Phi Runtime does not guarantee:

- truth
- morality
- organizational legitimacy
- legal compliance
- universal LLM safety
- correctness of a poorly specified integrity function

## 16. Certification target

A compliant runtime must pass:

- determinism tests
- replay tests
- receipt integrity tests
- invariant verification
- fuzz tests
- Monte Carlo stress tests
- performance tests
- reference vector tests
- TLA+ invariant model or equivalent formal model
- hash continuity tests

## 17. Version 1.0 deliverables

Version 1.0 consists of:

1. Execution Boundary Mathematics specification
2. Phi Runtime specification
3. VAIG Runtime specification
4. ACS Protocol specification
5. Python reference implementation
6. Rust reference implementation
7. TLA+ formal model
8. conformance test suite
9. benchmark suite
10. certification profile

## 18. Success criteria

A runtime is Phi Runtime v1.0 compliant only if it can demonstrate:

- deterministic execution under identical inputs
- every accepted transition satisfies the Integrity Preservation Theorem
- every rejected transition preserves the previous valid state
- every decision produces a verifiable cryptographic receipt
- every execution is replayable and independently auditable
- every implementation passes the conformance and benchmark suites

## 19. Product boundary

Phi Runtime is the execution-boundary engine.

VAIG is the governance runtime that builds the environment.

ACS is the protocol that carries requests, decisions and receipts.

Applications consume the protocol.

This separation is mandatory for product clarity.
