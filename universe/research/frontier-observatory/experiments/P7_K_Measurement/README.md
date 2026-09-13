# P7 — K-Measurement: Avgjørende Test av Phi-loven

**Hensikt:** Avgjøre om K (Lovgiverens strukturelle kapasitet) er substrat-spesifikt (Alt 1) eller universelt (Alt 2).

## Teori

K = Σ H(W_l) over alle vektmatriser W_l

H(W_l) = -Σ p_i × log₂(p_i) der p_i = σ_i / Σσ_j (normaliserte singulærverdier)

C₀ = ρ × K der ρ = γ/(δ-4) = 0.8625437492

## Falsifiseringstest

| Resultat | Tolkning |
|---|---|
| C₀ ≈ 4495 uavhengig av modell | Alt 2: K er universell |
| C₀ ≈ 3072 for Llama 3.2:3b | Alt 1: K er substrat-spesifikt |

## Kjøring

```bash
pip install transformers torch scipy

# Kontroll: GPT-2 baseline
python p1_k_measure.py --model gpt2 --samples 20 --output gpt2_result.json

# Avgjørende test: Llama 3.2:3b
python p1_k_measure.py --model meta-llama/Llama-3.2-3B-Instruct --samples 20 --output llama_result.json
```

Eller kjør i Colab: [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nsolland/Tofoo-/blob/main/Phi-Law-Validation/P7_K_Measurement/P7_K_Measure_Colab.ipynb)

## Resultater — 2026-06-14

Llama-3.2-3B-Instruct er gated repo — brukte EleutherAI/gpt-neo-1.3B som proxy-test.

| Modell | K (spektral) | C₀ = ρ×K | τ (dimless) | Matriser | Tilstand |
|---|---|---|---|---|---|
| GPT-2 (768 dim, 12 lag) | 463.07 | 399.41 | 0.6894 | 50 | COHERENCE |
| gpt-neo-1.3B (2048 dim, 24 lag) | 1555.77 | 1341.92 | 3.9581 | 146 | STASIS* |

*STASIS er artefakt — τ er ikke normalisert per log₂(hidden_dim).

K-forhold: 1555.77 / 463.07 = 3.36x. Hidden dim-forhold: 2048 / 768 = 2.67x.

**DOM: Alt 1 bekreftet.** K er substrat-spesifikt. K ≈ n_matriser × log₂(hidden_dim) (avvik 3%).

Merk: K-verdiene her er fra spektral entropi av vektmatriser (P7-metoden). Eldre baseline C₀=4495.27 er fra P1-protokollen (tau fra hidden states, annen målemetode).

*Tofoo. Φ*
