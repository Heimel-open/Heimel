# Scale-dependent intelligence falsification test

Status: executable falsification scaffold.

Question:

> Under a fixed substrate, does changing only the effective interaction scale cause a reproducible transition in integrated capability?

This is a test of the hypothesis that intelligence-like capability can be scale-dependent rather than a fixed property of a node or of the mesh in the abstract.

It does not infer consciousness and it does not treat QCD as evidence for intelligence. Asymptotic freedom is only the prompt for isolating scale as an experimental variable.

## Manipulated variable

Only:

```text
interaction_scale
```

The scale can represent a preregistered spatial, temporal, relational, or communication horizon. One run must use one definition consistently.

## Locked invariants

Every trial must carry identical values for:

```text
node_set
topology
initial_state
taskset
compute_budget
update_rule
```

If any of these differ, the evaluator returns `INSUFFICIENT_EVIDENCE`. A scale label is not enough: the experimental implementation must actually change the effective interaction horizon.

## Phenotype

Each trial reports four preregistered observables in [0,1]:

```text
task_success
cross_context_transfer
distributed_integration
counterfactual_adaptation
```

The phenotype score is their arithmetic mean.

## Default gates

These are harness defaults, not empirical claims:

```text
phenotype_threshold = 0.70
recovery_threshold  = 0.80
scale_margin        = 0.15
min_replicates      = 3
min_scales          = 3
```

A scale-dependent regime is `NOT_FALSIFIED_BY_DATA` only when:

1. at least one tested scale reproducibly reaches the phenotype regime;
2. at least one tested scale does not;
3. the mean phenotype gap between a qualifying and nonqualifying scale is at least `scale_margin`;
4. all declared non-scale invariants are identical.

Flat high performance falsifies scale dependence over the tested range. Flat low performance falsifies emergence over the tested range. Confounded runs are insufficient, not positive.

## Trial schema

```json
{
  "interaction_scale": 2.0,
  "replicate": 0,
  "invariants": {
    "node_set": "sha256:...",
    "topology": "sha256:...",
    "initial_state": "sha256:...",
    "taskset": "sha256:...",
    "compute_budget": "sha256:...",
    "update_rule": "sha256:..."
  },
  "phenotype": {
    "task_success": 0.81,
    "cross_context_transfer": 0.76,
    "distributed_integration": 0.79,
    "counterfactual_adaptation": 0.75
  }
}
```

Input is a JSON list of trials.

## Run

```bash
python experiments/scale_intelligence/scale_phase_falsifier.py trials.json
```

Test the harness:

```bash
cd experiments/scale_intelligence
pytest -q
```

## First empirical sweep

Use a logarithmic scale sweep, for example:

```text
1, 2, 4, 8, 16
```

For each scale, run at least three independently seeded replicates while keeping the invariant digests fixed.

The first run is deliberately cheap. Do not change topology, node count, model family, task distribution, compute budget, update rule, or initial-state construction to rescue a failed result.

Primary outcome:

```text
Does capability cross a preregistered regime boundary as scale alone changes?
```

If no: the scale-dependent intelligence hypothesis is falsified over the tested range.

If yes: the hypothesis survives this test, but the result still does not establish a universal law. The next intervention should test whether the transition follows spatial, temporal, or relational scale specifically.
