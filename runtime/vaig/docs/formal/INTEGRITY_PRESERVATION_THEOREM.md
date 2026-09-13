# Integrity Preservation Theorem

Status: formal note
Scope: supports VAIG execution-boundary reasoning
Boundary: does not expand VAIG Core beyond SYSTEM_MAP.md

This note formalizes a minimal transition-preservation result for governed execution.

It supports the VAIG execution-boundary pattern:

EvidenceCondition -> Intent -> Authorization -> Action or Refusal -> Receipt

It does not claim that VAIG governs truth, morality, organizational legitimacy, or general coherence theory.

## VAIG interpretation

- x_t: current execution state
- u_t: proposed action
- e_t: current EvidenceCondition or RiskContract context
- e_next: next evidence or policy context used for admission
- F: transition function
- K(e): admissible execution region under context e
- V(x,e): integrity valuation function
- Phi: transition gate

Core rule:

No transition may pass unless the resulting state remains inside the admissible execution region for the next context.

## Definitions

System:

x_next = F(x_t, u_t, e_t)

Integrity region:

K(e) = set of x in X such that V(x, e) <= 0

Phi filter:

Phi(x_t, u_t, e_t, e_next) = allow if and only if F(x_t, u_t, e_t) is in K(e_next)

## Theorem

If x_0 is in K(e_0), and every accepted transition passes the Phi filter, then x_t is in K(e_t) for all t >= 0.

## Proof

Basis: t = 0.

By assumption, x_0 is in K(e_0).

Induction step.

Assume x_t is in K(e_t).

Since the transition is allowed by Phi, F(x_t, u_t, e_t) is in K(e_next).

By the system definition, x_next = F(x_t, u_t, e_t).

Therefore x_next is in K(e_next).

By induction, integrity is preserved for all accepted transitions.

## Robust external context

When the next context is uncertain, replace e_next with a possible context set Ehat_next.

Robust Phi allows a transition only if the next state is inside K(e_candidate) for every e_candidate in Ehat_next.

This preserves the invariant for any materialized next context inside Ehat_next.

## Partial observation

When the full state is not directly observed, use a belief state.

The guarantee then becomes probabilistic rather than deterministic. A transition is allowed only if the probability of remaining inside K(e_next) is at least 1 - delta under the belief model.

## Human override

Override must be stated carefully.

If an override permits a transition where the next state is outside K(e_next), the integrity theorem no longer applies to that transition.

Therefore:

Override does not necessarily preserve integrity.
Override must preserve auditability and accountability.

A valid override path must generate an auditable receipt and move the system into one of:

- DEGRADED
- REVALIDATION_REQUIRED
- HALT

This aligns override with RRP, Receipt and WORM rather than treating override as a normal allowed transition.

## Receipt requirement

Every Phi decision should emit a receipt containing at least:

- time or sequence number
- current state hash
- proposed action hash
- context hash
- next context hash
- decision
- previous receipt hash
- current receipt hash

The receipt chain is not itself the integrity proof. It is the auditability mechanism that allows later verification of the decision path.

## Minimal TLA shape

IntegrityInvariant == V[x, e] <= 0

PhiFilter == LET next_x == F[x, u, e] IN V[next_x, e_next] <= 0

Next == either allow and advance to next_x, or block and keep state unchanged.

THEOREM Spec implies always IntegrityInvariant

A full TLA model must define Init, Spec, F, V, state domains, action selection and environment transition constraints.

## Failure conditions

The theorem does not apply if any of the following hold:

- x_0 is outside K(e_0)
- a transition bypasses Phi
- K(e) is wrongly defined
- V(x,e) does not represent the intended integrity boundary
- e_next is mis-specified
- override is treated as normal allow while violating K(e_next)
- receipts are emitted but the transition gate is not actually enforced

## VAIG placement

This note supports VAIG as execution-boundary governance.

It should be used to strengthen:

- action admission reasoning
- ACS and VACS receipt semantics
- RRP handoff semantics
- test fixtures for allowed, blocked, degraded and halted transitions

It should not be used to expand VAIG Core into:

- truth governance
- morality governance
- organizational legitimacy
- universal coherence theory
- long-term social continuity

Those boundaries remain controlled by SYSTEM_MAP.md.
