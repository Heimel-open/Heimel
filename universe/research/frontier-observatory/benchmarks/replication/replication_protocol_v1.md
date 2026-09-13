# τ Replication Protocol v1

Version: 1.0 (draft)  
Status: draft — not yet independently replicated  
Source: INDEX #92, tau/spec/tau_specification_v1.md

---

## Purpose

This protocol enables an external researcher to independently replicate τ measurements and verify the reference implementation. Replication does not require access to any private VALO constants or systems.

---

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.9+ | |
| numpy | ≥1.24 | Core math |
| torch | ≥2.0 | For model inference |
| transformers | ≥4.35 | HuggingFace |
| pytest | any | For test vectors |

```bash
pip install numpy torch transformers pytest
```

---

## Step 1 — Clone and verify the reference implementation

```bash
git clone https://github.com/nsolland/Index.git
cd Index
python -m pytest tau/tests/test_tau.py -v
```

Expected: 12 tests passing. If any test fails, record the failure and do not proceed — the implementation may have drifted from spec.

---

## Step 2 — Run against reference prompts

```bash
python tau/code/tau.py \
  --model gpt2 \
  --prompt "The quick brown fox jumps over the lazy dog" \
  --layer -1 \
  --json
```

Record the output. Expected τ: approximately 0.38 ± 0.05 (range is wide at this stage; narrower bounds pending more measurements).

Run all 10 prompts from `tau/datasets/prompts_v1.jsonl`:

```python
import json, subprocess

with open("tau/datasets/prompts_v1.jsonl") as f:
    for line in f:
        item = json.loads(line)
        result = subprocess.run(
            ["python", "tau/code/tau.py",
             "--model", "gpt2",
             "--prompt", item["prompt"],
             "--layer", "-1",
             "--json"],
            capture_output=True, text=True
        )
        print(item["id"], json.loads(result.stdout)["tau"])
```

---

## Step 3 — Record results

Create a results file at `tau/results/<model>_<date>_<your_handle>.jsonl` using the format in `tau/results/README.md`.

Required fields:
- `model_id` and `model_revision` (use `model.config._commit_hash` or git hash of model)
- `torch_version` and `transformers_version`
- `hardware` (CPU / GPU model)
- `measured_at` (ISO 8601)

---

## Step 4 — Submit for cross-validation

Open a PR to `nsolland/Index` adding your results file. In the PR description, note:
- Whether your τ values match the reference (within ±0.05 for this draft version)
- Any deviations from this protocol
- Hardware and software environment

---

## Step 5 — Extend to other models (optional)

The same measurement can be run on any HuggingFace model with `output_hidden_states=True`. Models of interest for cross-validation:

- `distilgpt2` (82M, smaller scale)
- `microsoft/phi-2` (2.7B)
- `mistralai/Mistral-7B-v0.1` (7B, requires ~14GB RAM)
- Any 70B+ model (requires significant hardware; results highly sought)

---

## What to report if values differ

If your measured τ values differ from the reference by more than ±0.05:

1. Check that model revision is identical (use `model.config._commit_hash`)
2. Check that tokenization is identical (`tokenizer.encode(prompt)` → same token IDs)
3. Check SVD implementation — both numpy and torch SVD should agree within 1e-6
4. Report the discrepancy as a comment on INDEX #92

---

## Scope of replication

This protocol replicates:

- The mathematical implementation of τ (spec Section 1)
- Determinism (spec Section 3)
- Test vector compliance (spec Section 5)

This protocol does NOT validate:

- Whether τ correlates with output quality (empirical question, separate study)
- Whether any particular τ range is "normal" (claim maturity M2 at best)
- Φ-Law theory or VALO operational constants (private; not part of this protocol)

---

## Contact

Open issues on `nsolland/Index` for protocol questions. Tag with label `tau`.
