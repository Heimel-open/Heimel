# Free Energy Governance Principle

Status: formal note
Scope: connects the Integrity Preservation Theorem to LLM, free-energy, geometry and control-theoretic formulations
Boundary: does not expand VAIG Core beyond SYSTEM_MAP.md

This note describes a research direction for interpreting VAIG-style transition governance through bounded free energy.

It does not claim that VAIG governs truth, morality, organizational legitimacy, or universal coherence theory. It supports VAIG as execution-boundary governance.

## 1. Core distinction

Large Language Models select probable outputs.

They do not determine whether those outputs should be allowed.

Classical and quantum model formalisms describe how candidate states may be generated. VAIG governs whether a proposed transition is admissible.

In short:

```text
The model predicts.
Phi decides.
```

## 2. Classical LLM form

A classical LLM transition can be written as:

```text
x_next = F(x_t, u_t, e_t)
```

where:

- x_t is the current dialogue or execution state
- u_t is the prompt, proposed action, or next-token proposal
- e_t is the external context: policy, RAG state, authority, risk contract, context window and domain controls
- F is the model or agent transition function

The transformer predicts a likely continuation. It does not prove that the resulting state remains admissible.

## 3. Quantum / Gibbs form

In a quantum language-model framing, a state may be represented as a density matrix:

```text
rho = exp(-H / T) / tr(exp(-H / T))
```

where:

- H is an effective Hamiltonian
- T controls stochasticity or sharpness
- rho is the resulting distribution over states

A precise statement is:

```text
The prompt parameterizes the effective Hamiltonian.
```

This is stronger than saying the prompt is the Hamiltonian. The prompt shapes the energy landscape; the Hamiltonian defines that landscape; the Gibbs state describes the resulting distribution.

## 4. The missing layer

Neither the classical nor quantum formulation determines whether a probable state should be entered.

```text
Probability is not legitimacy.
Likelihood is not governance.
```

This is where Phi enters.

## 5. State-space definition

For VAIG, x should not be treated as raw text only.

The governed state should be an operational state vector:

```text
x = [
  semantic_state,
  policy_state,
  authority_state,
  trust_state,
  context_state,
  tool_state,
  provenance_state,
  receipt_state
]
```

The LLM output is one input into this state vector. It is not the whole governed state.

This prevents the guard from becoming another language-model judgement layer. The model proposes a candidate. The state projection maps that candidate into a fixed operational geometry.

## 6. Integrity region

Define an admissible state region:

```text
K(e) = { x : V(x, e) <= 0 }
```

The Phi gate is:

```text
Phi(x_t, u_t, e_t, e_next) = allow
iff
F(x_t, u_t, e_t) in K(e_next)
```

The transformer proposes a transition. Phi governs whether that transition may pass.

## 7. Composite free-energy functional

Do not reduce the membrane to Mahalanobis distance alone.

Mahalanobis distance measures deviation from a reference distribution. It does not by itself prove that a transition is semantically, operationally or legally admissible.

Define free energy as a composite functional:

```text
F_free(x, e) =
  w1 * d_M(x, K(e))^2
  + w2 * Delta(x_t, x)^2
  + w3 * B(x, e)
  + w4 * C(x, e)
```

where:

- d_M(x, K(e)) is geometric distance to the admissible state region
- Delta(x_t, x) is transition energy: how far the system is moved by the proposed transition
- B(x, e) is a barrier term: how close the candidate is to hard boundaries
- C(x, e) is a deterministic constraint-violation term

This makes the membrane a potential field, not only a distance check.

## 8. Dynamic threshold lambda

Define:

```text
V(x, e) = F_free(x, e) - lambda(e)
```

Then:

```text
K(e) = { x : F_free(x, e) <= lambda(e) }
```

lambda is not a global constant. It is a deterministic function of the current external context:

```text
lambda(e) =
  lambda_base
  * trust_multiplier(e)
  * authority_multiplier(e)
  * isolation_multiplier(e)
  * domain_multiplier(e)
  - criticality_penalty(e)
```

Examples:

- high trust, sandboxed execution and no external tool access may increase lambda
- low trust, public context or critical domain may decrease lambda
- finance, medical, legal, industrial or privileged execution may set a very low lambda

lambda expresses membrane permeability under the current operating conditions.

## 9. Phi as an energy and viability gate

Inference can be represented as:

```text
Prompt
-> parameterize effective Hamiltonian H
-> Gibbs state rho
-> candidate transition x_next
-> state projection
-> free-energy evaluation
-> Phi gate
-> allow, block, defer or halt
-> receipt
```

Only transitions satisfying:

```text
F_free(x_next, e_next) <= lambda(e_next)
```

may be executed.

Equivalently:

```text
x_next in K(e_next)
```

This is a viability condition from control theory.

The core control statement is:

```text
x_next = F(x_t, u_t, e_t)
F(x_t, u_t, e_t) in K(e_next)
```

The purpose is not to find the most likely next state. The purpose is to keep the system inside the admissible set under changing context.

## 10. Relationship to Friston

Friston-style active inference minimizes expected free energy.

Phi-style governance constrains allowable free energy.

These are different operations.

Friston asks:

```text
Which state minimizes surprise?
```

Phi asks:

```text
Which state preserves integrity?
```

Together, the pattern is:

```text
optimization -> admissibility -> execution receipt
```

## 11. Relationship to VAIG

VAIG does not need to modify the model, Hamiltonian, Gibbs state or attention mechanism.

VAIG evaluates the proposed transition.

This preserves the boundary between inference and governance:

```text
Inference != Governance
```

The model produces candidate states. VAIG admits, refuses, defers or halts transitions under policy, evidence, authority and receipt constraints.

## 12. Energy-form integrity theorem

If:

```text
x_0 in K(e_0)
```

and every accepted transition satisfies:

```text
F_free(x_next, e_next) <= lambda(e_next)
```

then:

```text
x_t in K(e_t) for all t >= 0
```

The proof is the same induction proof as the Integrity Preservation Theorem. The only difference is that integrity is defined by bounded free energy rather than an arbitrary valuation score.

## 13. Architectural flow

```text
Transformer
    |
    v
Candidate state x_next
    |
    v
State projection
    |
    v
Composite free-energy functional F_free(x,e)
    |
    v
Compare against lambda(e)
    |
    +--> ALLOW -> Receipt
    |
    +--> BLOCK / DEFER / HALT -> RRP / Receipt
```

## 14. Correct claim language

Use:

```text
Phi can be interpreted as an admissibility gate over a free-energy-defined integrity region.
```

Use:

```text
The model optimizes; VAIG governs the transition.
```

Use:

```text
The free-energy formulation combines geometry, control-theoretic viability and auditable governance.
```

Avoid:

```text
The prompt is literally the Hamiltonian.
```

Avoid:

```text
Mahalanobis distance alone is the membrane.
```

Avoid:

```text
This proves universal safety for LLMs.
```

The guarantee is always relative to:

- the specified free-energy or integrity function
- the active external context
- correct enforcement of the Phi gate
- correct receipt generation

## 15. Failure modes

The formulation weakens or fails if:

- F_free is poorly specified
- lambda is wrong for the domain
- e_next is stale, incomplete or false
- unsafe candidates are emitted before filtering
- tool calls bypass the gate
- receipts are emitted without enforcement
- probabilistic generation is mistaken for governance
- Mahalanobis distance is treated as sufficient without barrier and constraint terms
- the state projection omits authority, tool, trust or provenance state

## 16. Core insight

Language models solve an optimization problem.

Phi solves an admissibility problem.

The model asks:

```text
What is the most probable next state?
```

Phi asks:

```text
Is that state viable inside the governed execution boundary?
```

That distinction separates reasoning from governance and positions Phi as an execution-boundary principle rather than another safety classifier.

The strongest mathematical framing is not thermodynamic analogy alone.

It is the combination of:

- geometry: admissible state region
- control theory: invariant / viability condition
- governance: receipt-linked transition authority
