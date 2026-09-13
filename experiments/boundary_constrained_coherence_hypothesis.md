# Boundary-Constrained Coherence Hypothesis

Canonical note for the revised formal hypothesis behind Phi-loven / LIM.

Status: M2 Formal hypothesis. Not independently replicated. This note corrects the earlier contraction-based formulation.

---

## Core claim

A dynamic system maintains identity over time when raw dynamics are allowed to operate, but only through a boundary operator that keeps the system inside an invariant stability region without erasing historical variation.

Short form:

```text
Identity is not convergence to one fixed point.
Identity is a historically dependent trajectory preserved inside admissible boundaries.
```

---

## Formal statement

Let:

```text
S_t   = system state at time t
I_t   = external input / perturbation at time t
G     = raw dynamics, generation, physics or update process
Omega = admissible stability region in state space
P_Omega = boundary / projection / admissibility operator
```

Then identity maintenance is modeled as:

```text
S_{t+1} = P_Omega(G(S_t, I_t))
```

where `P_Omega` is non-expansive:

```text
d(P_Omega(x), P_Omega(y)) <= d(x, y)
```

and `Omega` is an invariant admissible region under the governed dynamics.

---

## Why contraction was wrong as the main identity model

The earlier formulation used strict contraction:

```text
d(F(x), F(y)) <= k d(x, y), 0 < k < 1
```

This is appropriate for recovery, reset and homeostatic return, but not for identity itself.

A strictly contractive map collapses different initial histories toward the same attracting fixed point. That preserves stability, but it can erase historical identity.

Therefore:

```text
Homeostasis may use contraction.
Identity requires bounded historical continuity.
```

---

## Distinction

| Concept | Mathematical role | Interpretation |
|---|---|---|
| `G` | raw transition function | what the system would do without governance |
| `P_Omega` | non-expansive boundary operator | what is allowed to become the next state |
| `Omega` | admissible region | state-space where identity can persist |
| contraction | recovery / reset mode | pulls the system back toward a stable point |
| non-expansion | identity-preserving governance | prevents drift without erasing variation |

---

## Relation to Phi-loven

Phi-loven should be read as a boundary-governance hypothesis, not as a claim that every system converges to one universal fixed point.

```text
I = Phi(tau)
```

means:

```text
Identity is maintained by repeated boundary-constrained transformation over time.
```

Operational compression:

```text
No boundary -> drift.
No transformation -> stasis.
No history -> no identity.
No admissibility -> no legitimate state transition.
```

---

## Relation to VAIG / VALO

For AI governance:

```text
G = model / agent / workflow output
P_Omega = VAIG admissibility gate
Omega = policy, safety, evidence and authority constraints
S_{t+1} = allowed consequence-bearing state
```

VAIG should not force all outputs toward one ideal answer.

VAIG should prevent outputs from crossing outside the admissible region before they become action or consequence.

This is admissibility, not optimization.

---

## Falsification condition

The hypothesis is weakened if a system preserves a unique, historically specific identity under perturbation after the relevant boundary operator is removed or bypassed.

For a valid test, `P_Omega` must be operationalized as an explicit mechanism, not defined as the entire transition function.

Examples of explicit boundary mechanisms:

```text
cell membrane / ion channel
immune recognition threshold
attention mask / gating mechanism
policy gate / admissibility layer
market circuit breaker
flight envelope protection
WORM receipt + HALT boundary
```

A strong falsification test compares:

```text
controlled system:   S_{t+1} = P_Omega(G(S_t, I_t))
unbounded system:    S_{t+1} = G(S_t, I_t)
```

The hypothesis predicts that removing `P_Omega` increases drift, collapse, fragmentation or loss of recoverable identity under sufficiently strong perturbation.

---

## Claim maturity

Current status:

```text
M1 Conceptual: supported by structural analogy across domains
M2 Formal: stated as operator decomposition G + P_Omega
M3 Simulated: requires explicit paired simulations with and without P_Omega
M4 Empirical: requires domain-native data showing boundary removal causes identity degradation
M5 Replicated: requires independent reproduction
M6 Standardized: requires adoption in protocol or standard
```

Do not claim M4/M5 without independent artifacts.

---

## Recommended citation language

Use:

```text
Boundary-Constrained Coherence Hypothesis: identity maintenance in dynamic systems can be modeled as raw dynamics passed through a non-expansive admissibility operator that preserves historically dependent trajectories within an invariant stability region.
```

Avoid:

```text
Identity is produced by strict contraction to a fixed point.
```

Avoid:

```text
All stable systems prove Phi-loven.
```

---

## Next required work

1. Define `Omega` for one concrete domain.
2. Define the observer metric `d`.
3. Implement paired simulation: `G` alone vs. `P_Omega(G)`.
4. Specify falsification criteria before running.
5. Publish code and results for replication.
