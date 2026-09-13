# TOFOO relational rule recovery — Inspect AI

Status: **current evaluation implementation**  
Framework: **UK AI Security Institute Inspect AI**  
Task version: **1-0**

This package replaces the custom Colab evaluation harnesses as the normative implementation for new runs. The old v0–v3 files remain in the parent directory as experiment history only.

## Scope

This evaluation measures a narrow capability: **recovery of a hidden permutation rule from evidence distributed across participants**. It does not claim to measure general emergence.

Each generated world is validated before use:

- every participant's local evidence is ambiguous between at least two rules;
- the intersection of all participant evidence uniquely identifies the true rule;
- sample IDs are deterministic for a fixed seed;
- the target is a discrete A–H choice over a fixed rule catalog.

## Conditions

- `isolated` — one participant's ambiguous evidence only.
- `pooled_raw` — all participant evidence in one prompt.
- `structured_raw` — the same evidence deterministically grouped by participant.
- `central_iterative` — a central model receives all evidence for the same number of model calls as the relational condition and retains its prior guess.
- `relational_adaptive` — each call sees one participant's local evidence plus a deterministic governed field. A participant can support only a rule compatible with its own evidence; the field admits a rule only after support from every participant.

`isolated`, `pooled_raw`, and `structured_raw` use Inspect's built-in `multiple_choice()` solver and `choice()` scorer. The iterative conditions use small custom solvers because they require multiple model calls and persistent system state. Intermediate submissions are limited to `ANSWER: <LETTER>` and are covered by unit/E2E tests.

## Install

From this directory:

```bash
python -m pip install -e '.[dev]'
```

For local Hugging Face inference, Inspect's documented provider requires:

```bash
python -m pip install torch transformers accelerate
```

## Required quality gates

Before a real research run:

```bash
ruff check src tests
pytest -q
```

CI additionally executes real Inspect end-to-end smoke tests with `mockllm/model`; no external model API is allowed in that job.

Then run a **one-sample real-model smoke test** and inspect the log/trajectory before increasing the sample count. A wrong model answer is a score, not an instrument failure. A framework/runtime exception is an eval error.

## One-sample Qwen smoke tests

Use Inspect directly; Colab, if used at all, is only the GPU host.

```bash
inspect eval tofoo_relational_eval/pooled_raw \
  --model hf/Qwen/Qwen2.5-1.5B-Instruct \
  -M device=cuda:0 \
  -M do_sample=false \
  --max-connections 1 \
  --limit 1 \
  --log-model-api \
  --log-dir logs/qwen-smoke-pooled
```

Then test the materially different relational solver:

```bash
inspect eval tofoo_relational_eval/relational_adaptive \
  --model hf/Qwen/Qwen2.5-1.5B-Instruct \
  -M device=cuda:0 \
  -M do_sample=false \
  --max-connections 1 \
  --limit 1 \
  --log-model-api \
  --log-dir logs/qwen-smoke-relational
```

Inspect the complete sample trajectories before proceeding:

```bash
inspect view --log-dir logs/qwen-smoke-relational
```

## Full condition set

Only after the one-sample real-model checks have been manually reviewed:

```bash
inspect eval-set \
  tofoo_relational_eval/isolated \
  tofoo_relational_eval/pooled_raw \
  tofoo_relational_eval/structured_raw \
  tofoo_relational_eval/central_iterative \
  tofoo_relational_eval/relational_adaptive \
  --model hf/Qwen/Qwen2.5-1.5B-Instruct \
  -M device=cuda:0 \
  -M do_sample=false \
  --max-connections 1 \
  --log-model-api \
  --log-dir logs/qwen-full
```

Task parameters can be changed with Inspect's `-T` option, for example:

```bash
inspect eval tofoo_relational_eval/pooled_raw \
  --model mockllm/model \
  -T seed=20260820 -T worlds=1 -T participants=3 -T operators=3 -T rounds=3 \
  --limit 1
```

## Interpretation

The primary comparison is not encoded as a custom pass/fail claim in the harness. Inspect logs each condition independently. Analysis should compare the relational score against the strongest central/pooled control and report token/model-call budgets from the Inspect logs.

A positive difference in one run is **signal discovery only**. It requires repeated seeds, multiple model sizes/families, budget analysis, trajectory review, and independent reproduction before stronger claims.

## Reproducibility

Record at minimum:

- repository commit SHA;
- task version;
- full model identifier;
- Inspect version;
- task parameters and seed;
- model arguments/generation settings;
- Inspect `.eval` logs.

The package pins `inspect-ai==0.3.251`. Model/runtime dependencies are deliberately not silently upgraded by notebook cells.

See `QUALITY.md` for the gate checklist used for this evaluation.
