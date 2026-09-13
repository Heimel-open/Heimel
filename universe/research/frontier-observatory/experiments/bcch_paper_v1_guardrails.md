# BCCH Paper v1 Guardrails

Working note for turning the Boundary-Constrained Coherence Hypothesis into a credible paper draft.

Status: M2 formal framing. Not a universal law. Not independently replicated.

---

## Core correction

The paper must not treat strict contraction as the mathematical basis of identity.

Strict contraction is useful for homeostasis, recovery and reset. It is not sufficient for identity maintenance.

A contractive map collapses different histories toward the same attracting state. That may preserve stability, but it can erase historical identity.

Therefore:

```text
Homeostasis = return toward stability.
Identity = historically dependent trajectory preserved inside admissible boundaries.
```

---

## Canonical formulation

Use:

```text
S_{t+1} = P_Omega(G(S_t, I_t))
```

where:

```text
S_t       = system state at time t
I_t       = external input / perturbation
G         = raw dynamics / model / physics / generation
P_Omega   = explicit boundary, projection or admissibility operator
Omega     = admissible viability region
```

The identity of the system is not a point. It is the admissible path maintained through state space over time.

Use this sentence:

```text
A system's identity is not its equilibrium; it is the admissible trajectory it maintains through state space while preserving historical continuity.
```

---

## Required properties of P_Omega

`P_Omega` should be treated as:

```text
explicit
operationalized
non-expansive
viability-preserving
observer-metric dependent
separate from raw dynamics G
```

Do not define `P_Omega` as the whole transition function. That makes the hypothesis tautological.

A valid paper must identify the actual mechanism that functions as the boundary.

Examples:

```text
cell membrane / ion channels
immune recognition threshold
attention mask / gating mechanism
policy gate / admissibility layer
control barrier function
flight envelope protection
market circuit breaker
WORM receipt + HALT boundary
```

---

## Omega

Do not describe `Omega` only as a vague stability interval.

Better language:

```text
Omega is an admissible invariant set, or viability region, relative to an observer-defined metric d.
```

For real systems, `Omega` may be soft, probabilistic or time-dependent. The paper should not require all biological or social systems to have hard static boundaries.

Use:

```text
Omega_t may be compact, bounded, or practically constrained relative to the measurement regime.
```

Avoid:

```text
All systems have one universal Omega.
```

---

## What to cite as related work

Strong and relevant:

```text
viability theory
control barrier functions
Markov blankets
active inference
homeostasis
autopoiesis
control theory
resilience theory
invariant sets
Lyapunov stability
basin stability
```

Use these as related work, not as proof that BCCH is true.

---

## What to quarantine

Move to speculative extensions or remove from paper v1:

```text
Planck constant as observer signature
wavefunction collapse as boundary enforcement
Holographic Space-Time claims
universal law of form in the universe
strong claims about all existence
unverified quantum metaphysics
```

These may be interesting, but they will weaken a first paper.

---

## Falsification design

A sharp test must compare:

```text
bounded system:    S_{t+1} = P_Omega(G(S_t, I_t))
unbounded system:  S_{t+1} = G(S_t, I_t)
```

The hypothesis predicts that removing or bypassing the explicit boundary operator increases:

```text
drift
collapse
fragmentation
loss of recoverable identity
policy violation
authority violation
unbounded consequence propagation
```

For AI systems, do not merely test whether the model can preserve a persona.

Test whether it preserves:

```text
role boundaries
policy boundaries
evidence requirements
authority constraints
action limits
refusal under missing admissibility
```

This is the real VAIG-relevant test.

---

## AI-specific distinction

Internal stabilizers inside `G` are not enough.

```text
softmax    = internal competition / normalization
LayerNorm  = numerical stabilization
attention  = contextual selection
RLHF       = learned behavioral shaping
policy     = normative boundary
VAIG       = runtime admissibility boundary
```

The key claim is not that raw models have no stabilizers.

The key claim is:

```text
Internal model stabilization can preserve form, but governable identity requires an explicit semantic, normative or authority-bearing boundary operator.
```

---

## Recommended paper title

```text
Boundary-Constrained Coherence: Identity Maintenance as Viability-Preserving Admissible Trajectories
```

Alternative AI-focused title:

```text
Boundary-Constrained Coherence: Runtime Admissibility for Consequence-Bearing AI Systems
```

---

## Recommended paper structure

1. Introduction: identity as trajectory, not substance.
2. Formal model: raw dynamics plus boundary operator.
3. Related work: viability, CBFs, Markov blankets, autopoiesis, control theory.
4. Falsification protocol: with and without explicit `P_Omega`.
5. AI case: VAIG as runtime admissibility operator.
6. Limitations: no universal-law claim; replication required.

---

## Safe conclusion language

Use:

```text
BCCH is a candidate formal framing for studying identity maintenance in dynamic systems where stability depends on explicit boundary, viability or admissibility constraints.
```

Avoid:

```text
BCCH proves the underlying logical law for the existence of form in the universe.
```

Use:

```text
The hypothesis is supported by structural convergence with existing theories, but requires domain-specific operationalization and falsification.
```

Avoid:

```text
The literature confirms BCCH unconditionally.
```

---

## Current maturity

```text
M1: conceptual convergence across domains
M2: formal operator decomposition G + P_Omega
M3: pending paired simulations
M4: pending empirical domain-native validation
M5: pending independent replication
M6: not applicable yet
```

Do not claim beyond M2/M3 until artifacts exist.
