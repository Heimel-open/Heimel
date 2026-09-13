# Effective Rank Density as an Order Parameter for Transformer Workspace Dynamics

Status: ACTIVE research protocol / empirical run pending

## Core claim

Coherent transformer reasoning is not characterized by maximal spectral compression, but by stabilization within an intermediate effective-rank regime.

A global workspace does not emerge from maximal compression or maximal dispersion. P10 tests whether coherent reasoning is associated with a stable intermediate spectral regime.

## Correct formalization

Framleis acts on the representational state, not directly on tau.

```math
X_{t+1} = F(X_t; \sigma_t, u_t)
```

```math
\tau_t = \tau(X_t)
```

```math
V(X) = \operatorname{dist}(\tau(X), G)^2
```

Where:

- `X_t` is the full representational state, such as a hidden-state matrix or residual-stream state.
- `F` is a candidate Framleis transition operator on `X`.
- `u_t` is an optional controlled search condition used by the adaptive-sweep experiment.
- `tau(X)` is an observable/order parameter derived from the singular-value spectrum of `X`.
- `G` is the configured Goldilocks band: the intermediate effective-rank regime.
- `V(X)` measures distance from the Goldilocks band, not raw tau minimization.

## Goldilocks regimes

Tau is not monotonic quality. Lower is not always better.

- Too low tau: candidate signature of spectral collapse, repetition, mode collapse or rigid/stasis state.
- Tau inside G: candidate signature of adaptive coherence.
- Too high or unstable tau: candidate signature of diffusion, fragmentation or failure to stabilize.

Hallucination must not be defined as high tau only. It can be unstable tau, oscillation, or a falsely stable wrong attractor. These remain empirical hypotheses until measured on representative models and tasks.

## J-space: corrected boundary

The July 2026 primary source does not define J-space as the transition mechanism itself.

Gurnee et al. define J-space as a sparse subframe of the model's representational space identified through J-lens vectors. In the reported workspace layers, only a small number of these directions are meaningfully active at once, J-space explains a minority of activation variance, and its evolving contents can mediate internal reasoning and flexible downstream use.

Therefore P10 now separates:

```text
full representational state X_t
→ unknown selection / transition dynamics
→ sparse J-space readout P_J(X_t)
→ operationally relevant workspace content
```

and independently:

```text
X_t → tau(X_t)
```

The primary source explicitly leaves open what mechanism determines what enters J-space. P10 treats that as an empirical gap, not as an already solved transition regime.

Primary sources:
- https://www.anthropic.com/research/global-workspace
- https://transformer-circuits.pub/2026/workspace/

## Adaptive Cognitive Sweep extension

The experimental hypothesis is documented in:

`../../docs/theories/2026-08-10-jspace-framleis-adaptive-cognitive-sweep.md`

Controlled phases:

```text
BROAD_SCAN
→ TARGET_LOCK
→ DISCONFIRMING_SWEEP
→ UNCERTAINTY_MAP
→ CANDIDATE_SET
```

These are experimental conditions, not claimed native modules in the transformer.

Predicted observable signatures are phase-specific changes in sparse J-space coordinates: target alignment, workspace concentration, counterevidence recruitment, reorganization, and eventual candidate-set stability.

An operational fixed point is defined on repeated J-space stability, not on convergence of the full state or tau.

## P10 + J-space coupled hypothesis

The stronger P10 claim can now be tested as two independent requirements:

```text
stable decision-relevant CANDIDATE_SET in J-space
AND
tau(X_t) inside configured G
```

A trace can satisfy one and fail the other. The falsifier preserves that distinction.

## Executable falsification harness

Run:

```bash
python3 experiments/P10_Transformer_Workspace_Dynamics/sweep_falsifier.py trace.jsonl
```

Every empirical observation should carry a stable `trace_id`. Turnover is isolated per trace, so interleaved tasks do not contaminate one another.

Phase comparisons are paired within the same `trace_id`. Repeated observations are averaged inside each trace first, then traces are averaged with equal weight. A task with more samples therefore cannot dominate the multi-task result merely because it was sampled more often.

All scientific thresholds must be pre-registered and passed explicitly. The CLI exposes:

```text
--min-target-gain
--min-concentration-gain
--min-counter-gain
--min-disconfirming-turnover
--max-candidate-turnover
--min-candidate-tau-fraction
```

Optionally test the P10 spectral coupling with an explicitly configured band:

```bash
python3 experiments/P10_Transformer_Workspace_Dynamics/sweep_falsifier.py trace.jsonl \
  --goldilocks-low <LOW> --goldilocks-high <HIGH>
```

When spectral coupling is enabled, every CANDIDATE_SET observation must carry tau. Missing tau produces `INSUFFICIENT_EVIDENCE`; missing values are never silently removed from the coupling test.

The built-in numerical defaults are harness defaults for development/tests only. They are not a scientific preregistration.

The harness emits:

- `CONSISTENT`
- `FALSIFIED`
- `INSUFFICIENT_EVIDENCE`

Overall `NOT_FALSIFIED_BY_TRACE` must never be interpreted as scientific validation.

## Minimum empirical protocol

Measure open models across matched conditions while preserving raw per-layer/token states:

1. BROAD_SCAN control.
2. TARGET_LOCK with target dissociated from trivial lexical echo where possible.
3. DISCONFIRMING_SWEEP requiring explicit search for an alternative or counterexample.
4. UNCERTAINTY_MAP condition where unresolved alternatives are behaviorally relevant.
5. repeated CANDIDATE_SET readouts before final output.

For every observation:

- assign a stable `trace_id` for the task/run
- extract hidden state
- compute J-lens sparse coordinates when instrumentation permits
- compute effective-rank density tau
- retain target and disconfirming concept labels independently of generated output
- compare against matched non-J-space / prompt controls

## Original P10 observational conditions remain

The broader tau program still measures:

1. Correct answer
2. Hallucination
3. Repetition / mode collapse
4. Multi-step reasoning
5. Ambiguous input

Predictions remain hypotheses:

- Correct reasoning stabilizes more often inside `G`.
- Repetition tends toward collapse below `G`.
- Hallucination fails to stabilize reliably inside `G`.
- Multi-step reasoning shows structured variation rather than simple monotonic tau change.
- Ambiguous input may show oscillation, bimodality or delayed stabilization.

## Paper sequence

1. Effective Rank Density as an Order Parameter for Transformer Workspace Dynamics
   - empirical tau measurement only
2. Spectral Phase Transitions in Transformer Workspace Formation
   - Goldilocks regime and phase-transition framing
3. Framleis Dynamics of Workspace Stabilization
   - mathematical operator, J-space selection hypothesis and attractor tests
4. Toward a Dynamical Theory of Global Workspace Formation
   - broader neuroscience implications only after empirical support

## Scope discipline

Do not frame P10 as a theory of consciousness.

Do not equate J-space with Framleis.

Do not equate a synthetic unit-test PASS with empirical evidence.

Use this phrasing:

> This may have implications for theories of conscious access, but the present work is restricted to transformer workspace dynamics.
