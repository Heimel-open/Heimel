# Execution Boundary Mathematics

Status: draft v1.0
Scope: mathematical foundation for Phi Runtime
Boundary: supports VAIG execution-boundary reasoning without expanding VAIG Core scope

Execution Boundary Mathematics defines the minimum mathematical structure required to preserve integrity across governed state transitions.

## 1. Core problem

Inference systems generate candidate states.

Governed systems must decide whether those states may be entered.

The problem is not:

```text
What is the most probable next state?
```

The problem is:

```text
Does this transition preserve the system's continuous integrity under changing external conditions?
```

## 2. State transition

Let:

```text
x_next = F(x_t, u_t, e_t)
```

Where:

- x_t is current operational state
- u_t is proposed transition or action
- e_t is current external context
- F is the transition function

## 3. State projection

Raw model output is not the governed state.

Define:

```text
P: O -> X
```

Where:

- O is raw output: text, JSON, plan, tool call or action packet
- X is the operational state space

A projected state must include the governance-relevant dimensions:

- semantic state
- policy state
- authority state
- trust state
- context state
- tool state
- evidence state
- provenance state
- receipt state

## 4. Admissible state region

Define:

```text
K(e) = { x in X : V(x, e) <= 0 }
```

K(e) is the admissible state region under external context e.

## 5. Composite integrity functional

Define:

```text
V(x, e) = F_free(x, e) - lambda(e)
```

Where:

```text
F_free(x, e) =
  w1 * d_M(x, K(e))^2
  + w2 * Delta(x_t, x)^2
  + w3 * B(x, e)
  + w4 * C(x, e)
```

Terms:

- d_M: geometric deviation from admissible state region
- Delta: transition energy
- B: barrier potential near hard boundaries
- C: deterministic constraint violations

## 6. Dynamic lambda

lambda(e) defines current membrane permeability.

It is deterministic and context-dependent:

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

## 7. Phi decision operator

Define:

```text
Phi(x_t, u_t, e_t, e_next) = ALLOW
iff
F(x_t, u_t, e_t) in K(e_next)
```

Equivalent energy form:

```text
Phi = ALLOW iff F_free(x_next, e_next) <= lambda(e_next)
```

## 8. Integrity Preservation Theorem

If:

```text
x_0 in K(e_0)
```

and every committed transition passes Phi, then:

```text
x_t in K(e_t) for all t >= 0
```

Proof: induction over committed transitions.

## 9. Viability framing

The Phi condition is also a viability condition from control theory:

```text
F(x_t, u_t, e_t) in K(e_next)
```

The goal is to keep the system inside the admissible set under changing context.

## 10. Receipt invariant

Every decision emits a receipt.

Receipts do not prove correctness of V or lambda.

They prove that the decision path is replayable and tamper-evident.

Minimum invariant:

```text
DecisionTaken => ReceiptWritten
ReceiptHash_t = hash(Receipt_t, ReceiptHash_{t-1})
```

## 11. Commit invariant

Only ALLOW may commit x_next.

All other decisions preserve current valid state:

```text
ALLOW -> x' = x_next
BLOCK -> x' = x
DEFER -> x' = x
HALT -> x' = x
```

## 12. Claim boundary

This mathematics proves preservation relative to:

- the specified state projection
- the specified integrity functional
- the specified lambda function
- the specified environment
- correct enforcement of Phi

It does not prove universal safety, truth, legal compliance or moral correctness.
