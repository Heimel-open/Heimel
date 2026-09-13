# Compounding Intelligence — Colab v0

Status: EXPERIMENTAL / FALSIFICATION-FIRST
Date: 2026-08-19

## Purpose

Cheap first test of four linked hypotheses:

1. persistent experience can improve a frozen base model over repeated episodes;
2. consolidation can outperform raw episodic memory;
3. full trajectories can contain more reusable learning signal than final outputs alone;
4. governed admission can preserve useful learning without allowing the learner to write directly to authoritative state.

This is not a claim of recursive self-improvement, consciousness, or a universal `Cmin`.

## Experimental conditions

```text
A STATELESS
model -> task -> answer -> reset

B PERSISTENT_RAW
model -> task -> answer -> feedback -> episodic memory -> next task

C PERSISTENT_CONSOLIDATED
experience -> candidate rule -> replay evaluation -> ADMIT/REJECT/UNRESOLVED -> governed state -> next task
```

The notebook uses a frozen model and a synthetic hidden-rule world so that improvement can come only from state carried across episodes, not weight updates.

## Core invariant

```text
candidate learning != admitted learning
```

The consolidation process may propose a rule. It never writes authoritative state directly.

```text
experience
-> candidate learning
-> replay test
-> ADMIT / REJECT / UNRESOLVED
-> governed_state
```

Hard invariant:

> **NO_DIRECT_GOVERNED_LEARNING_WRITE_PATH**

If a candidate bypasses admission, the run is invalid.

## Trajectory comparison

For the same episodes the notebook can expose either:

```text
OUTPUT_ONLY
input -> correct final answer
```

or:

```text
FULL_TRAJECTORY
input -> attempted answer -> feedback -> correction / outcome
```

The first v0 test is intentionally small. A positive result is only a signal for a larger frozen-corpus study.

## Colab use

Open `compounding_intelligence_colab_v0.ipynb` in Google Colab, select a GPU runtime, then run top-to-bottom.

Default model is deliberately small enough for common Colab GPU sessions. The model ID is configurable in the first configuration cell.

Outputs are written under:

```text
/results/
  manifest.json
  trajectories.jsonl
  governed_state.json
  scores.csv
  summary.json
```

Copy `/results` to Drive or download it before the runtime is destroyed.

## Primary metrics

- episode accuracy over time;
- holdout accuracy before vs after accumulated experience;
- stateless vs persistent delta;
- raw-memory vs consolidated-state delta;
- output-only vs full-trajectory delta;
- admitted / rejected / unresolved candidate counts;
- direct governed-write violations (must equal zero).

## Stop conditions

Stop or redesign if:

- persistent conditions do not exceed stateless control;
- gains disappear on blind holdout tasks;
- gains require leakage of correct answers from holdout into memory;
- the learner can write governed state without admission;
- results are not reproducible across seeds.

## Next step if v0 survives

Run the same harness across a model-size ladder and frozen worlds to estimate a task/environment-specific threshold rather than assuming a universal `Cmin`.
