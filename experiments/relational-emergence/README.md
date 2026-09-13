# TOFOO relational capability evaluation

Status: EXPERIMENTAL / FALSIFICATION-FIRST  
Date: 2026-08-19

## Current implementation

New research runs use the **Inspect AI** implementation in:

```text
experiments/relational-emergence/inspect_eval/
```

Start with `inspect_eval/README.md` and `inspect_eval/QUALITY.md`.

The current evaluation name is deliberately narrow: **TOFOO relational rule recovery**. It tests whether a governed distributed condition can recover a hidden rule from evidence that is ambiguous in each local shard but jointly identifying. It is not, by itself, a general emergence benchmark.

## Framework

The evaluation now uses UK AI Security Institute **Inspect AI** for task execution, model providers, scoring, logging, and reproducibility. Ordinary conditions use Inspect's built-in multiple-choice solver/scorer. Custom code is limited to the stateful central and relational conditions plus deterministic world/state logic.

## Conditions

```text
isolated
pooled_raw
structured_raw
central_iterative
relational_adaptive
```

The central iterative and relational conditions use the same configured number of model calls. Token/model usage is taken from Inspect logs rather than a parallel home-grown accounting system.

## Historical implementations

`relational_emergence_v0.py` through `relational_emergence_v3.py` and the old Colab notebooks are retained only as experiment history. They are **not normative research instruments** and should not be used for new results.

## Execution

Colab is optional infrastructure only. The evaluation logic lives in the normal Python package under `inspect_eval/` and is run with `inspect eval` / `inspect eval-set`. See `inspect_eval/README.md` for the tested commands and required quality gates.
