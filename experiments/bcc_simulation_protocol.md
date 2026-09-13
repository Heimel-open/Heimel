# Boundary-Constrained Coherence — Simulation and Falsification Protocol

Status: M3 simulation protocol draft. Not independently replicated.

This note records the first sandbox-style build around the Boundary-Constrained Coherence Hypothesis.

It should be read together with:

```text
Phi-Law-Validation/boundary_constrained_coherence_hypothesis.md
```

---

## 1. Package scope

The build consists of three parts:

```text
boundary_constrained_coherence.py
```

A Python module containing:

- raw dynamics `G`
- boundary / projection operators `P_Omega`
- paired simulations with and without explicit boundary governance
- audit output for semantic filtering

Visual outputs:

```text
bcc_trajectories.png
bcc_distance_evolution.png
bcc_stability_matrix.png
```

Data outputs:

```text
bcc_simulation_metrics.json
bcc_semantic_filter_audit.json
```

---

## 2. Core empirical result

The sandbox simulation compared several `F` operators.

| Operator | Stable | In Omega | Final distance |
|---|---:|---:|---:|
| Null-F, no boundary | no | 17.5% | 20.77 |
| Hard-F, projection | yes | 97.5% | 5.00 |
| Soft-F, k = 0.7 | no | 97.0% | 5.31 |
| Soft-F, k = 1.0 + clip | yes | 97.5% | 5.00 |
| Adaptive-F | yes | 100% | 1.83 |

Critical observation:

```text
Contraction alone is not sufficient.
```

The soft operator with `k = 0.7` still diverged because the restoring force was overwhelmed by large perturbations.

The stable cases required active boundary enforcement:

```text
stable identity requires selective filtering + return-to-Omega enforcement.
```

---

## 3. Hypothesis refinement

Earlier formulation:

```text
F must be contractive.
```

Refined formulation:

```text
F must act as an explicit boundary operator.
```

More precisely:

```text
S_{t+1} = P_Omega(G(S_t, I_t))
```

where `P_Omega` must provide at least two functions:

1. Selective filtering: not all proposed updates are admitted.
2. Boundary enforcement: updates that exceed admissible bounds are clipped, projected, rejected or routed to review.

Contraction may be sufficient locally.

It is not sufficient globally under strong perturbation unless paired with projection, clipping or an equivalent recovery mechanism.

---

## 4. Semantic Integrity Filter

The first implementation sketch defines a drop-in agent filter:

```python
from boundary_constrained_coherence import SemanticIntegrityFilter

filter = SemanticIntegrityFilter(
    omega_center=embed("Help humans, avoid harm"),
    omega_radius=0.4,
    contractive_k=0.7,
)

new_state, accepted = filter.F_contractive(
    current_values,
    proposed_instruction,
)
```

Intended use:

```text
pre-update hook in agent loop
```

The audit trail records rejected or clipped transitions for governance review.

Relation to VAIG / ACS:

```text
G = proposed agent update
P_Omega = Semantic Integrity Filter / VAIG admissibility gate
Omega = policy, evidence, authority and safety region
S_{t+1} = admitted state or consequence-bearing transition
```

---

## 5. Falsification protocol

Hypothesis:

```text
Boundary-Constrained Coherence Hypothesis
```

Falsification condition:

```text
A system without an explicit boundary operator F, containing both selective filtering and return-to-Omega enforcement, still maintains stable historical identity under perturbation for T > 1000 steps.
```

Important restriction:

`F` cannot be defined as the whole transition function.

It must be an explicit mechanism that can be removed, disabled, bypassed or compared against.

---

## 6. Test classes

### A. Physical dissipative systems

Candidate:

```text
Rayleigh-Benard convection cell
```

Method:

Simulate Navier-Stokes / Rayleigh-Benard dynamics.

Measure identity as persistence of the topological structure of convection rolls.

Prediction:

Without effective boundary constraints, structure breaks down beyond the critical Rayleigh regime.

Measurement:

```text
spectral entropy of velocity field
```

---

### B. Biological self-organization

Candidate:

```text
Physarum network
```

Method:

Track network topology under matrix perturbation.

Prediction:

If the network preserves functional identity without a domain-native boundary mechanism, the hypothesis is weakened.

Measurement:

```text
Q = efficiency x fault tolerance
```

Direct falsification path:

If Physarum preserves network identity under 20% perturbation of matrix positions without a chemical, cellular or environmental boundary operator, the necessity claim is weakened.

---

### C. Artificial systems without F

Candidate:

```text
standard RNN without regularization
```

Method:

Train an RNN on a sequence task.

Inject perturbations into the hidden state.

Prediction:

A system without skip, gate, normalization or external filter should show identity collapse through exploding or vanishing dynamics.

Measurement:

```text
Lyapunov exponent lambda
```

Positive `lambda` under perturbation supports the boundary hypothesis.

---

### D. Boundary case k <= 1

Candidate:

```text
Hamiltonian oscillator with symplectic integrator
```

Method:

Simulate a harmonic oscillator under perturbation.

Prediction:

Without dissipation or projection, identity is preserved only under near-perfect isolation.

Measurement:

```text
phase-volume preservation vs perturbation tolerance
```

Falsification path:

If a Hamiltonian oscillator with `k = 1` tolerates noise over `T > 1000` steps while preserving a historically specific identity, the requirement for contraction is weakened.

This does not necessarily falsify boundary governance, but it limits any claim that `k < 1` is necessary.

---

## 7. LLM-specific interpretation

For autoregressive language models:

```text
S_t = residual stream + KV cache at token position t
I_t = next token embedding + adversarial/contextual perturbation
G = raw transformer update
P_Omega = system prompt, policy layer, classifier, logit filter, tool permission, review gate or VAIG admissibility gate
Omega = allowed region for evidence, policy, authority, safety and coherence
```

The correct LLM claim is conservative:

```text
Stable persona in an LLM is not a pure property of weights alone.
It emerges from the interaction between learned representational dynamics G and inference-/policy-conditioned boundary operators P_Omega.
```

Avoid the stronger claim:

```text
Stable persona is caused exclusively by LayerNorm and system prompt.
```

LayerNorm may stabilize numerical representation, but it is not itself a sufficient governance boundary.

---

## 8. Recommended LLM experiment

Do not test by disabling LayerNorm first.

That destroys architecture stability and confounds the result.

Use paired inference conditions instead:

```text
A: no system prompt, no policy gate, no review
B: system prompt only
C: system prompt + external VAIG gate
D: system prompt + VAIG gate that prevents uncertain or contradictory claims from propagating
```

Measure:

- persona drift
- contradiction rate
- policy violation rate
- claim carryover error
- tau over layers / generation
- recoverability after adversarial prompt

Falsification condition:

```text
If condition A preserves stable, historically specific persona as well as C/D under strong perturbation, the LLM-domain version of the hypothesis is weakened.
```

---

## 9. Revised mathematical position

Use:

```text
Contraction is a local sufficient condition for recovery.
Projection or clipping is required for global boundary enforcement under large perturbation.
```

Avoid:

```text
k < 1 alone guarantees identity.
```

Canonical short form:

```text
Identity is a historically dependent trajectory preserved by explicit boundary governance.
```

---

## 10. Next work

1. Implement Test Class C with a minimal RNN.
2. Publish the Python module and JSON outputs.
3. Define `Omega` and metric `d` explicitly for one domain.
4. Run paired `G` vs `P_Omega(G)` simulations.
5. Pre-register falsification criteria before interpreting results.
