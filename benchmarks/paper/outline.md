# Paper Outline — τ as Coherence Metric for LLM Hidden States

Status: outline draft  
Target venue: arXiv cs.LG (primary) + cs.CL (cross-list)  
Relationship to Spor 2 paper: this outline is the public-safe replication companion

---

## Title candidates

1. "Spectral Entropy as a Coherence Metric for Large Language Model Hidden States"
2. "τ: A Reproducible Coherence Measurement for Transformer Hidden States"
3. "Measuring Spectral Coherence in LLM Representations: A Replication Study"

---

## Abstract (draft)

We introduce τ (tau), a scalar coherence metric derived from the spectral entropy of large language model hidden states. τ ∈ [0,1] measures how concentrated or diffuse the singular value spectrum of a hidden state representation is, with higher values indicating greater spectral concentration and potentially greater representational coherence. We provide a formal specification, a reference implementation, and test vectors enabling independent replication. We report τ measurements on three publicly available models at 124M–7B scale (GPT-2, Phi-2, Mistral-7B). We observe that τ increases with model scale in this range and that τ varies systematically across prompt types. We make no claim that τ predicts output quality or that any particular τ range is optimal. τ is proposed as a candidate observable for further study.

---

## 1. Introduction

- Motivation: LLM representations are high-dimensional and difficult to characterize simply
- Gap: No standard scalar coherence metric for hidden states
- Contribution: τ as a reproducible, model-agnostic measurement
- Scope limitation: this paper is empirical; we do not derive τ from theory

## 2. Related work

- Spectral analysis of neural representations (general)
- Intrinsic dimensionality of LLM representations
- Other coherence/complexity metrics in NLP
- Distinction from: perplexity, token probability, attention entropy

## 3. Method

- Definition: τ = 1 - H_norm(S(h)) (from spec v1)
- SVD computation
- Normalization choice and rationale
- Input/output specification
- Determinism guarantee

## 4. Experiments

### 4.1 Models

| Model | Scale | Source |
|---|---|---|
| GPT-2 | 124M | HuggingFace `gpt2` |
| Phi-2 | 2.7B | HuggingFace `microsoft/phi-2` |
| Mistral-7B | 7B | HuggingFace `mistralai/Mistral-7B-v0.1` |

### 4.2 Measurement protocol

- Layer selection: last hidden layer
- Tokenization: default HuggingFace tokenizer, max 128 tokens
- Reference prompts: `datasets/prompts_v1.jsonl` (10 prompts across 5 domains)

### 4.3 Results

- τ by model (table)
- τ by prompt domain (table)
- Layer-by-layer τ profile for GPT-2 (figure)
- Scaling trend (figure: log N vs τ)

## 5. Analysis

- Scaling observation: τ increases with model scale in [124M, 7B] range
- Domain effect: coherent narrative prompts → higher τ than token-list prompts
- Layer effect: τ typically increases from input to output layer
- Limitations:
  - Only 3 models measured
  - No models above 7B
  - No cross-architecture comparison (all decoder-only)
  - τ not validated against downstream task performance

## 6. Discussion

- τ as a candidate metric: what further evidence would be needed
- Relationship to representational quality (speculative; flagged as such)
- What τ does not measure
- Future work: 70B+ models, encoder architectures, multilingual models

## 7. Conclusion

τ is a reproducible, model-agnostic scalar derived from hidden state spectra. We report measurements on 3 models and provide a replication protocol. We do not claim τ measures output quality or that any threshold is universal.

---

## Appendix

- A: Full specification (pointer to tau/spec/tau_specification_v1.md)
- B: Test vectors
- C: Raw measurement table

---

## Status

| Section | Status |
|---|---|
| Abstract | Draft |
| Introduction | Outline only |
| Related work | Not written — literature search needed |
| Method | Complete (from spec) |
| Experiments — 124M | Complete |
| Experiments — 2.7B | Complete |
| Experiments — 7B | Complete |
| Experiments — 70B+ | Not done (requires RunPod A100 or similar) |
| Analysis | Outline only |
| Discussion | Outline only |
| Figures | Not created |
| Replication check | Not done — waiting for external replication |

---

## Notes

- Do not mention Φ-Law, LIM, or VALO operational constants in this paper
- All threshold/boundary values (if discussed) must be derived in-paper, not imported from private theory
- arXiv endorsement required: seek from existing cs.LG author
