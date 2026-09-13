# P8 — Lambda-test og tredje K-datapunkt

**Hensikt:** Loese to aapne spoersmaal fra P7 i én kjøring.

## Spoersmaal 1: Skaleringsformel

K = n_matriser × log₂(hidden_dim) — holder den for tre ulike arkitekturer?

| Modell | Forventet K | Forventet C₀ |
|---|---|---|
| GPT-2 (124M) | 50 × 9.58 = 479 | 413 |
| gpt-neo-1.3B | 146 × 11.0 = 1606 | 1385 |
| gpt-neo-2.7B | ~200 × 11.32 = 2264 | 1953 |

## Spoersmaal 2: Lambda-analyse

Kalibreringsproblemet fra K18: C₀_P1_GPT2 = 4495.27, C₀_P7_GPT2 = 399.41, lambda = 11.25.

Notebooken prover alle kjente aggregeringer av tau (siste lag, sum alle lag,
skalert med seq_len, hidden_dim, log2^2) og rapporterer forholdet til C₀_P1.
Aggregeringen som gir ratio ~1.0 er den som forklarer P1-baselinen.

## Kjøring

Aapne i Colab: [![Open in Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/nsolland/Tofoo-/blob/main/Phi-Law-Validation/P8_Kalibrering/P8_Lambda_Colab.ipynb)

Bruk **High-RAM runtime** (Runtime > Change runtime type) for gpt-neo-2.7B (~11GB).

## Resultater

Fyll inn etter kjøring:

| Modell | K_malt | K_pred | Avvik | C₀_spektral |
|---|---|---|---|---|
| GPT-2 | TBD | 479 | TBD | TBD |
| gpt-neo-1.3B | TBD | 1606 | TBD | TBD |
| gpt-neo-2.7B | TBD | 2264 | TBD | TBD |

Lambda-kandidat med ratio naermest 1.0: TBD

*Tofoo. Phi.*
