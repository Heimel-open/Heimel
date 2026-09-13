# Relational seed minimum-state experiment

Status: executable falsification scaffold

Question:

> What is the smallest retained relational seed that can, under fixed nourishment, regenerate a declared integrated-availability phenotype?

This experiment does not measure phenomenal consciousness. It evaluates a bounded phenotype defined by six preregistered observables:

- cross access;
- workspace integration;
- temporal continuity;
- history dependence;
- counterfactual reorganization;
- causal effect of current integrated state on next selection.

## Required trial schema

```json
{
  "seed_size": 12,
  "condition": "intact",
  "replicate": 0,
  "phenotype": {
    "cross_access": 0.82,
    "workspace_integration": 0.78,
    "temporal_continuity": 0.80,
    "history_dependence": 0.74,
    "counterfactual_reorganization": 0.77,
    "self_effect_on_next_selection": 0.81
  }
}
```

Input is a JSON list of such trials.

Required conditions for the first run:

```text
intact   = retained relational organization preserved
shuffled = same seed volume, relation identity/topology shuffled
```

Additional controls such as `node_only`, `no_recurrence`, `no_memory` and `no_feedback` belong in later intervention runs.

## Preregistered evaluation

For each trial, phenotype score is the arithmetic mean of the six declared metrics.

Default thresholds in the harness are test defaults, not empirical claims:

```text
phenotype_threshold = 0.70
recovery_threshold  = 0.80
relation_margin     = 0.15
min_replicates      = 3
```

Candidate minimum seed `s*` is the smallest intact seed size whose recovery rate reaches the configured recovery threshold.

A relation-specific result additionally requires the mean intact phenotype at `s*` to exceed the matched shuffled control by at least `relation_margin`.

Possible outputs:

```text
NOT_FALSIFIED_BY_DATA
FALSIFIED_BY_DATA
INSUFFICIENT_EVIDENCE
```

`NOT_FALSIFIED_BY_DATA` is not validation of consciousness. It means only that the supplied dataset contains a candidate minimum seed and the matched relation-shuffle control did not explain the result.

## Run

```bash
python experiments/relational_seed/seed_falsifier.py trials.json \
  --phenotype-threshold 0.70 \
  --recovery-threshold 0.80 \
  --relation-margin 0.15 \
  --min-replicates 3
```

## First empirical sweep

Hold constant:

```text
model/substrate family
training or interaction budget
current task distribution
compute budget
nourishment schedule
evaluation probes
```

Vary only retained seed size and the declared control transformation.

For every seed size:

```text
1. start from a mature system with the target phenotype
2. destroy the active mature phenotype
3. retain only the preregistered seed
4. regrow under identical nourishment
5. measure the six phenotype components without using self-report as evidence
6. repeat with matched shuffled relation seed
```

The important output is not merely whether recovery occurs. It is the recovery curve across compression and the causal gap between intact and shuffled seeds.
