# τ Specification v1 — Coherence Metric for LLM Hidden States

Version: 1.0 (draft)  
Status: candidate specification — not validated as universal claim  
Source: INDEX #92

---

## 1. Definition

τ (tau) is a scalar in [0, 1] that measures the spectral coherence of LLM hidden state representations.

Formal definition:

```
τ(h) = 1 - H_norm(S(h))
```

Where:

- `h` is the hidden state tensor at a given model layer, shape `[sequence_length, hidden_dim]`
- `S(h)` is the singular value spectrum of `h` (computed via SVD)
- `H_norm(S)` is the normalized spectral entropy of `S`

### 1.1 Normalized spectral entropy

```
λᵢ = sᵢ² / Σⱼ sⱼ²          # normalized squared singular values (sᵢ from SVD)
H(S) = -Σᵢ λᵢ log(λᵢ)      # spectral entropy (nats)
H_norm(S) = H(S) / log(n)   # normalized by log(min(seq_len, hidden_dim))
τ = 1 - H_norm(S)           # coherence: 1 = maximally coherent, 0 = maximally diffuse
```

### 1.2 Interpretation

| τ range | Interpretation |
|---|---|
| Near 1.0 | Highly coherent; variance concentrated in few directions |
| Near 0.5 | Mixed; distributed representations |
| Near 0.0 | Diffuse; near-uniform spectral energy distribution |

---

## 2. Inputs and outputs

### Inputs

| Parameter | Type | Description |
|---|---|---|
| `model_id` | string | HuggingFace model identifier (name + revision) |
| `layer_index` | int | Layer index (-1 = last layer) |
| `prompt` | string | Input text |
| `tokenizer_kwargs` | dict | Optional tokenizer settings (padding, max_length, etc.) |

### Outputs

| Field | Type | Description |
|---|---|---|
| `tau` | float in [0,1] | Spectral coherence score |
| `H` | float | Raw spectral entropy (nats) |
| `H_norm` | float | Normalized spectral entropy |
| `n_singular_values` | int | Number of singular values used |
| `model_id` | string | Model identifier |
| `layer_index` | int | Layer used |
| `seq_len` | int | Sequence length after tokenization |
| `hidden_dim` | int | Hidden dimension of the layer |

---

## 3. Determinism requirements

- Same `(model_id, layer_index, prompt, tokenizer_kwargs)` → same `τ` (within floating-point tolerance)
- Tolerance: ±0.001 for τ across platforms with identical model weights
- SVD implementation: use `numpy.linalg.svd` or `torch.linalg.svd` with full_matrices=False
- No random sampling; full hidden state tensor used

---

## 4. Scope constraints

### What this specification covers

- A single measurement of τ for one prompt at one layer of one model
- A deterministic, reproducible algorithm

### What this specification does NOT cover

- The Φ-Law theory or its operational constants (C₀, α, τ_min, τ_max)
- Any claim about universality of τ across architectures
- Any production threshold values (these are system-specific; if used operationally, inject via environment variables)
- Calibration against specific coherence thresholds

---

## 5. Test vectors (declared)

The following test vectors must hold within ±0.002 tolerance on a canonical GPT-2 implementation:

| Prompt | Layer | Expected τ | Note |
|---|---|---|---|
| `"The quick brown fox"` | -1 | 0.38 ± 0.02 | Short, coherent |
| `"a b c d e f g h i j k l m n o p q r s t u v w x y z"` | -1 | 0.21 ± 0.02 | Random tokens; low coherence expected |
| `"Once upon a time there was a kingdom"` | -1 | 0.42 ± 0.02 | Narrative opening |

Note: These test vectors are approximate. They may need recalibration against a specific `gpt2` (124M) revision. The test file in `tests/test_tau.py` documents the exact revision used.

---

## 6. Falsification criteria

This specification is falsified (not the metric) if:

1. The same `(model_id, layer_index, prompt)` produces τ values varying by more than ±0.01 across identical hardware and software environments (non-determinism failure)
2. τ = 1.0 for all inputs regardless of prompt (implementation error — constant output)
3. τ < 0 or τ > 1 for any valid input (range violation)

The underlying coherence hypothesis (that τ correlates with output quality or semantic coherence) is a separate empirical question and is NOT part of this specification.

---

## 7. Claims bounded by this specification

| Allowed claim | Not allowed claim |
|---|---|
| "τ is a reproducible measurement of spectral coherence" | "τ measures model 'intelligence'" |
| "τ varies across models and layers" | "τ predicts output quality" |
| "τ can be measured on any transformer model" | "τ is a universal law" |
| "These 3 models measured at τ = X" | "All models should have τ in [A, B]" |

---

## 8. Version history

| Version | Date | Change |
|---|---|---|
| 1.0 | 2026-06-27 | Initial draft |
