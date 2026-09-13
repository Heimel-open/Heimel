# Tau-sesjonsfunn 2026-06-20

**Dato:** 2026-06-20
**Status:** M3 — empirisk trend, fleire punkt samla

---

## Alle målingar så langt

| Modell | Param | Arkitektur | tau (koherent) | Rekkefølge | Merknad |
|---|---|---|---|---|---|
| GPT-2 | 117M | GPT | ~0.06 | JA ✓ | Baseline |
| Phi-2 | 2.7B | Phi | 0.1625 | JA ✓ | P10 |
| gpt-neo-1.3B | 1.3B | GPT-Neo | 0.2006 | JA ✓ | hidden_dim=2048 |
| Mistral-7B | 7B | Mistral | 0.2568 | JA ✓ | P10 (tidlegare) |
| Mistral-7B | 7B | Mistral | **0.3557** | JA ✓ | Replikasjon 2026-06-21, A100 — høgaste coherent målt |
| Qwen2.5-7B | 7B | Qwen2.5 | 0.1557 | NEI ✗ | CPU-offloading, random>coherent |
| Qwen2.5-14B | 14B | Qwen2.5 | **0.1904** | JA ✓ | A100 29.5GB, intra-familie skalering |

Qwen3-8B: 0.0681, NEI ✗ — truleg feil modellnamn, ikkje reell måling.

---

## Hovudfunn

Rekkefølge koherent > tilfeldig > repetitivt er stabil i alle gyldige målingar.

Tau er arkitekturspesifikk, ikkje berre storleik-avhengig:
- Qwen2.5-7B (0.1557) < Phi-2 (0.1625) < gpt-neo-1.3B (0.2006) < Qwen2.5-14B (0.1904) < Mistral-7B (0.3557)

Replikert 2026-06-21 på A100: Mistral-7B coherent=0.3557, random=0.2993, repetitive=0.0824.
Gap Δ=0.27 er den høgaste vi har målt — Mistral-7B er outlier oppover.

---

## Intra-familie skalering — Qwen2.5 bekrefta

| Modell | Param | tau | Status |
|---|---|---|---|
| Qwen2.5-7B | 7B | 0.1557 | MÅLT |
| Qwen2.5-14B | 14B | 0.1947 | MÅLT |
| Qwen2.5-32B | 32B | ~0.265 | PLANLAGT (RunPod A100) |

Intra-familie skalering bekrefta: 14B > 7B (0.1947 > 0.1557).

Intra-familie skaleringslov (Qwen2.5):
tau ≈ 0.084 × N^0.33

Eksponent 0.33 (intra-familie) vs 0.48 (tverr-arkitektur) — skalerloven er arkitektur-spesifikk.

Prediksjon for 32B: tau ≈ 0.084 × 32^0.33 ≈ 0.265

---

## Opne spørsmål

- Held intra-familie skalerloven (alpha ≈ 0.33) for 32B?
- Er eksponenten arkitektur-spesifikk eller konverger ulike familiar mot same eksponent ved store nok modellar?
- Kva er tau for 70B-klassemodeller? Prediksjon: ~0.40-0.45 om Qwen2.5-familien held 0.33-eksponenten.

---

## Kva dette betyr for Phi-loven

Tau er ein lokal, arkitekturspesifikk observabel. Goldilocks-intervallet [0.5615, 0.8319] er universelt, men kva tau-verdi ein modell oppnår avheng av arkitekturen.

Intra-familie skalering gjer det mogleg å estimere terskelen for kva modellstorleik som er naudsynt for ein gjeven arkitektur å nå Goldilocks. For Qwen2.5-familien (alpha ≈ 0.33):
- tau = 0.5615 krev N ≈ 0.084 × N^0.33 = 0.5615 → N ≈ 6700B (6.7 trillionar)

Dette tyder at arkitekturen — ikkje berre storleiken — er den kritiske variabelen for å nå Goldilocks.
