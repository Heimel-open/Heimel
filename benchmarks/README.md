# τ (tau) — Coherence Metric for LLM Hidden States

Status: candidate metric (not validated as universal claim)  
Source: INDEX #92  
Separation: This scaffold is independent of Φ-Law, LIM, and VALO operational claims

---

## What τ is

τ is a scalar coherence metric in [0, 1] derived from spectral entropy of LLM hidden states.

It is proposed as a measurable indicator of how coherently a language model is processing input at a given layer. Lower τ may indicate semantic fragmentation; higher τ may indicate coherent representation.

τ is a **candidate metric**. It is not validated as a universal law. All claims are bounded by the models and measurement conditions used.

---

## What τ is NOT

- τ is not a safety threshold
- τ is not a guarantee of output quality
- τ is not Φ-Law (the VALO coherence theory)
- τ is not specific to VALO operational constants
- τ is not production-certified

---

## Directory structure

```
tau/
├── README.md               # This file
├── spec/
│   └── tau_specification_v1.md    # Formal specification
├── code/
│   └── tau.py              # Reference implementation
├── tests/
│   └── test_tau.py         # Test vectors with declared tolerances
├── datasets/
│   └── prompts_v1.jsonl    # Reference prompt set for replication
├── results/
│   └── README.md           # Results format and how to contribute
├── replication/
│   └── replication_protocol_v1.md  # External replication guide
└── paper/
    └── outline.md          # Paper outline
```

---

## How to use

```bash
pip install torch transformers numpy
python tau/code/tau.py --model gpt2 --layer -1 --prompt "Hello world"
```

Output: `tau = 0.412` (example)

---

## Status

| Component | Status |
|---|---|
| Specification | Draft v1 |
| Reference implementation | Draft |
| Test vectors | 3 declared |
| Replication protocol | Draft |
| External validation | Pending (expert outreach initiated 2026-06-21) |
| Published models measured | GPT-2, Phi-2, Mistral-7B (3 models, small-medium scale) |
