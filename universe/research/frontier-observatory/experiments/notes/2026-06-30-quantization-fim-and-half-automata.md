# Quantization, FIM perturbation and the half-automata hypothesis

Date: 2026-06-30
Status: research note / interpretive hypothesis
Maturity: M1/M2, with links to P1-P9 as possible explanatory frame

---

## Short conclusion

Yes, this strengthens the half-automata assumption.

It does not prove P1-P9 by itself, but it gives a cleaner mechanism for why the results appear: the deployed model is not the same dynamical object as the trained model. Once weights are quantized, the model's local geometry changes. If the empirical Fisher Information Matrix changes, then the model's sensitivity landscape changes too.

That means governance cannot safely treat a model as a stable abstract object. It must govern the concrete running instance: model, quantization, hardware, context, state and execution path.

This is directly aligned with LIM / VAIG.

---

## External paper

Reference:

Alekberli & Karimov, 2026, *Spectral Perturbation of the Empirical Fisher Information Matrix under Weight Quantization*, arXiv:2606.28432.

Relevant claim as understood from the paper summary:

- weight quantization perturbs the empirical Fisher Information Matrix;
- the dominant eigenvalue lambda_max is directionally pushed upward under generic quantization noise assumptions;
- the result is based on Weyl-type spectral perturbation reasoning;
- the authors are careful that the bound is directional and assumption-dependent, not a full closed-form prediction of effect size.

Operational reading:

```text
FP32 model geometry != Q4 model geometry
```

Therefore:

```text
governance calibrated on one representation may fail on another representation
```

---

## Link to the half-automata hypothesis

The half-automata hypothesis says that an LLM-like system behaves like an incomplete automaton:

```text
state + input -> scored next-state candidates
```

but it lacks the full second half:

```text
admissibility -> invariant preservation -> accountable transition
```

So the model has transition capacity, but not self-governing closure.

Quantization strengthens this interpretation because it shows that the transition surface itself is implementation-dependent. The same nominal model can become a different semi-discrete transition system after compression.

In that sense, a quantized model is not merely a cheaper copy. It is a new half-automaton with a changed boundary geometry.

---

## Why this helps explain P1-P9

P1-P9 can be read as repeated observations of the same structural pattern:

```text
unfiltered transition capacity drifts
filtered transition capacity stabilizes
```

The FIM / quantization result gives a plausible lower-level mechanism for why this happens in model systems:

1. The model is sensitive to local geometric perturbations.
2. Quantization changes that geometry.
3. Changed geometry changes transition probabilities and error surfaces.
4. Without a filter, drift is expressed directly as unstable behavior.
5. With LIM / Phi filtering, only admissible transitions are allowed to persist.

This supports the interpretation that LIM is not only a semantic or policy filter. It functions as the missing closure layer for an otherwise incomplete transition system.

---

## Mapping to current protocols

P1 - LLM coherence:
The unfiltered GPT-2 run can be interpreted as a half-automaton executing transitions without invariant-preserving closure. LIM adds the missing admissibility boundary.

P5 - Swarm coherence:
Each agent can be read as a local transition system. Without a shared admissibility rule, local updates amplify drift. With Phi filtering, the swarm obtains boundary memory and converges into coherent behavior.

P6 - MECHA governance:
The v1.0 bug showed that execution without a complete veto/admissibility check can enter invalid finalized states. That is the formal version of the half-automata problem: transition exists, but closure is incomplete.

P7-P9 - spectral / lambda / two-level structure:
These are the most directly connected. If spectral sensitivity changes across model representation, then the measured K/lambda/C0_outer behavior should be treated as deployment-specific, not model-universal.

---

## Important limitation

This should not be stated as:

```text
The paper proves Phi-loven.
```

Better statement:

```text
The paper supports a key operational premise behind Phi-loven and VAIG: the deployed model instance has its own geometry, so governance must be runtime-bound and instance-calibrated.
```

Even stronger:

```text
Quantization turns the model into a different half-automaton. LIM/VAIG is the missing admissibility layer that decides which transitions are allowed to become identity-preserving state.
```

---

## Research implication

P10 should include a deployment-calibration clause:

```text
tau, dtau/dt, K_spectral and related coherence signals must be measured on the actual deployed representation, including quantization format and runtime environment.
```

Do not calibrate only on FP32 or training-time models if the operational system runs Q4, GGUF, GPTQ, AWQ or another compressed representation.

---

## Canonical compression

```text
Quantization changes geometry.
Changed geometry changes transition behavior.
Transition without admissibility is only half an automaton.
LIM supplies the missing closure condition.
VAIG makes that closure executable.
```
