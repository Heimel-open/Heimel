# τ Results — Format and Contribution Guide

---

## Results file format

Each results file is a JSONL file where each line is one τ measurement:

```json
{
  "model_id": "gpt2",
  "model_revision": "11c5a3d",
  "layer_index": -1,
  "prompt_id": "p001",
  "prompt": "The quick brown fox...",
  "tau": 0.412,
  "H": 1.823,
  "H_norm": 0.588,
  "n_singular_values": 20,
  "seq_len": 12,
  "hidden_dim": 768,
  "hardware": "CPU / CUDA T4 / etc",
  "torch_version": "2.1.0",
  "transformers_version": "4.40.0",
  "measured_at": "2026-06-27T00:00:00Z"
}
```

## File naming convention

```
results/<model_slug>_<date>_<author_slug>.jsonl
```

Example: `results/gpt2_2026-06-27_nsolland.jsonl`

---

## How to contribute results

1. Run `tau/code/tau.py` against prompts from `tau/datasets/prompts_v1.jsonl`
2. Record output in the JSONL format above (include model revision hash)
3. Open a PR adding your results file to `tau/results/`
4. Include in the PR: hardware, software versions, any deviations from the reference protocol

---

## Current results

| Model | Scale | Measured τ (mean) | Layer | Date | Source |
|---|---|---|---|---|---|
| GPT-2 | 124M | ~0.38 | last | 2026-06 | Tofoo internal |
| Phi-2 | 2.7B | ~0.42 | last | 2026-06 | Tofoo internal |
| Mistral-7B | 7B | ~0.45 | last | 2026-06 | Tofoo internal |

Note: Values above are approximate from internal measurement runs. Formal result files pending replication protocol completion.

---

## Interpretation constraint

Results here record τ values for specific models under specific conditions. They do not constitute a claim that any particular τ range is "correct" or "optimal". See `spec/tau_specification_v1.md` Section 6 for claim boundaries.
