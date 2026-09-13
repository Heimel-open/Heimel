# J-space / Framleis adaptive cognitive sweep

Date: 2026-08-10
Status: research hypothesis and falsification protocol
Issue: #87

## Boundary first

J-space and Framleis are not the same object.

The July 2026 Anthropic / Transformer Circuits work defines J-space as a sparse, verbalizable subframe of model representations. In workspace layers, only a small number of J-lens directions are meaningfully active at once; the J-space component accounts for a minority of activation variance. Its contents can mediate internal reasoning, directed modulation and flexible downstream use.

The primary source also leaves an explicit open problem: the mechanism that determines what enters J-space is not known.

This note places the hypothesis exactly in that gap.

Primary sources:
- https://www.anthropic.com/research/global-workspace
- https://transformer-circuits.pub/2026/workspace/

## Empirical observations used here

Epistemic status: empirical_observation, limited to the systems and experiments reported by Gurnee et al. (2026).

1. J-space is a sparse component of the full representational state, not the full state itself.
2. Workspace-like J-space content is strongest in an intermediate layer regime rather than uniformly across depth.
3. J-space contents evolve across layers and can contain intermediate concepts before output.
4. Directed instructions can modulate J-space content.
5. J-space interventions can causally redirect some reasoning and reporting behaviors.
6. The reported work does not identify the mechanism that selects what enters J-space.

None of these observations establishes Framleis, Adaptive Cognitive Sweep, consciousness, or a general theory of cognition.

## Mathematical separation

Epistemic status: mathematical_definition.

Let `X_t` denote the full representational state at an internal processing index `t`.

Let

```text
J_t = P_J(X_t)
```

be a sparse J-space readout or projection, operationalized by J-lens sparse decomposition when that instrumentation is available.

Let

```text
X_(t+1) = F(X_t; sigma_t, u_t)
```

be a candidate Framleis transition model over the full representational state.

`u_t` is an experimentally assigned cognitive-search condition:

```text
BROAD_SCAN
→ TARGET_LOCK
→ DISCONFIRMING_SWEEP
→ UNCERTAINTY_MAP
→ CANDIDATE_SET
```

The phase labels are experimental labels. They are not asserted to be native modules or literal states inside the model.

The central separation is:

```text
Framleis candidate dynamics: X_t → X_(t+1)
Observable workspace content: P_J(X_t)
Spectral observable: tau(X_t)
```

J-space is therefore an observation surface for selected representational content. Framleis is a candidate model of the transition dynamics. Tau is a separate scalar observable of the full state. No identity between the three is assumed.

## C-JFS-001 — adaptive sweep / workspace-selection hypothesis

Epistemic status: hypothesis.

If a transformer uses phase-dependent selection dynamics resembling an adaptive cognitive sweep, then controlled changes in search objective should produce reproducible, phase-specific changes in J-space contents while the underlying task is held as constant as possible.

Predicted signatures:

1. BROAD_SCAN: relatively distributed workspace occupancy across task-relevant alternatives.
2. TARGET_LOCK: increased J-space mass on the target and increased workspace concentration.
3. DISCONFIRMING_SWEEP: recruitment of counterevidence / alternative concepts and measurable workspace reorganization.
4. UNCERTAINTY_MAP: explicit representation of unresolved alternatives or uncertainty-bearing concepts where the task supports them.
5. CANDIDATE_SET: stabilization of a small decision-relevant workspace set after the disconfirming pass.

This is not a claim that the model implements these five named phases internally. It is a claim that controlled experimental conditions corresponding to those functions should leave distinguishable traces if the proposed selection dynamics are real.

## Operational fixed point

Epistemic status: mathematical_definition.

An operational fixed point is not defined as convergence of the full hidden state and not as convergence of tau.

For repeated candidate-set observations `J_t`, define workspace turnover by total variation distance between normalized sparse J-space coordinates:

```text
D_J(J_t, J_(t+1)) = 1/2 * sum_i |p_t(i) - p_(t+1)(i)|
```

A candidate set is operationally stable over a pre-registered window when `D_J` remains below a pre-registered threshold while the decision-relevant content remains sufficient for the task.

This permits the full representational state to continue changing while the operationally relevant workspace content has stabilized.

## C-JFS-002 — P10 spectral coupling hypothesis

Epistemic status: hypothesis.

P10 already treats effective-rank density `tau(X_t)` as an order parameter for workspace dynamics. The stronger coupled hypothesis is:

```text
workspace stabilization in CANDIDATE_SET
AND
tau(X_t) inside the configured Goldilocks regime G
```

should co-occur more reliably for coherent reasoning than in matched failure controls.

The two conditions are deliberately independent. A stable J-space candidate set outside `G`, or tau inside `G` without stable decision-relevant J-space content, falsifies the simple coupled account for that trace.

No monotonic decrease or increase in tau is predicted during the sweep.

## Competing explanations that must be separated

Epistemic status: falsification_criterion.

A positive-looking trace is not sufficient. At minimum, the experiment must distinguish:

1. Lexical echo: target words appear because the prompt mentions them.
2. Output preparation: J-space merely reflects the imminent answer rather than selection dynamics.
3. Generic prompt entropy: concentration changes because one condition is linguistically narrower.
4. Non-J-space state change: the same effect occurs equally in matched control directions, so it is not specific to the workspace.
5. Tau-only account: spectral state predicts the result without phase-specific J-space reorganization.
6. Uncontrolled task difficulty: conditions differ because one is simply harder.

The strongest design keeps task, model, decoding, token budget and surface form matched while experimentally dissociating target, counterevidence and expected output.

## F-JFS-001 — primary falsification conditions

Epistemic status: falsification_criterion.

The adaptive sweep hypothesis is weakened or falsified if, on a pre-registered multi-task dataset with matched controls:

- TARGET_LOCK does not increase target-aligned J-space mass relative to BROAD_SCAN.
- TARGET_LOCK does not increase workspace concentration beyond matched prompt controls.
- DISCONFIRMING_SWEEP does not recruit counterevidence or reorganize J-space beyond matched controls.
- repeated CANDIDATE_SET observations do not become more stable than the disconfirming transition.
- the same signatures are reproduced by lexical/prompt controls without the proposed functional manipulation.
- matched non-J-space directions explain the effects as well as or better than J-space coordinates.

One failed task is not enough to reject a cross-task hypothesis. Thresholds, aggregation rules and minimum task count must be pre-registered before an empirical run.

## F-JFS-002 — spectral coupling falsification

Epistemic status: falsification_criterion.

The P10 coupling is falsified in its simple form if operationally stable, correct candidate sets systematically occur outside the configured Goldilocks regime, or if tau is inside the regime without any corresponding stabilization of decision-relevant J-space content.

This criterion tests coupling. It does not falsify J-space itself and does not by itself falsify Framleis as a broader transition model.

## Executable falsifier

Epistemic status: implementation_claim.

`experiments/P10_Transformer_Workspace_Dynamics/sweep_falsifier.py` implements deterministic trace metrics for:

- normalized J-space concentration and entropy
- target mass
- disconfirming mass
- weighted workspace turnover
- operational fixed-point stability
- optional P10 Goldilocks coupling

Each observation carries a `trace_id`. Stateful turnover is computed only against the preceding observation with the same `trace_id`, so multiple tasks can be interleaved without cross-task contamination. Candidate-set stability uses only repeated candidate readouts within the same trace.

All falsification thresholds are exposed as CLI arguments. The built-in defaults are test-harness defaults only; an empirical run must record explicit pre-registered values before measurement.

The executable uses `CONSISTENT`, `FALSIFIED`, and `INSUFFICIENT_EVIDENCE`. A consistent synthetic trace is reported only as `NOT_FALSIFIED_BY_TRACE`; it is never labeled validation.

The accompanying unit tests validate the falsifier's mechanics using synthetic traces. They are not empirical evidence for C-JFS-001 or C-JFS-002.

## Empirical next run

Required data per observation:

```json
{
  "trace_id": "task-001",
  "phase": "TARGET_LOCK",
  "workspace": {"concept_a": 0.7, "concept_b": 0.2},
  "targets": ["concept_a"],
  "disconfirming": ["concept_c"],
  "tau": 0.71
}
```

For an actual J-lens run, `workspace` must come from measured sparse J-space coordinates, not from generated text or chain-of-thought.

The empirical run should include matched controls and preserve raw layer/token readouts so the phase labels can be re-scored independently. It must also store the exact threshold set used by the falsifier.

## Interpretation limit

If the predictions survive, the defensible claim is narrow:

Controlled search conditions systematically reorganize a sparse workspace in a manner consistent with the proposed Framleis adaptive-sweep dynamics.

It would not prove that J-space is Framleis, that the model has human-like attention, or that the mechanism is biologically homologous.
