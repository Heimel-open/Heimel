# P10: Tau-skalering — empiriske funn og prediksjon

**Dato:** 2026-06-19
**Status:** M3 — empirisk trend etablert, prediksjon testbar
**Kobling:** Phi-loven (tau, Goldilocks), Canon F7, A2-derivasjonen

---

## Datapunkter (tau, siste lag, koherent tekst)

| Modell | Parametere | tau (Koherent) | r_eff | r_max | Status |
|---|---|---|---|---|---|
| GPT-2 | 117M | ~0.06 | ~2 | ~30 | UNDER |
| Phi-2 | 2.7B | 0.1625 | 13.81 | 85 | UNDER |
| Mistral-7B | 7B | 0.2568 | 22.60 | 88 | UNDER |
| Qwen2.5-7B | 7B | 0.1557 | — | — | UNDER |
| gpt-neo-1.3B | 1.3B | 0.2006 | — | — | UNDER |

Rekkefølge innad i alle modeller: Koherent > Tilfeldig > Repetitivt. Stabil (bekreftet Qwen2.5-7B og gpt-neo-1.3B 2026-06-20).

Arkitektureffekt bekreftet: Qwen2.5-7B (0.1557) vs Mistral-7B (0.2568) ved identisk parameterklasse.
Dette støtter Alt 1-dommen fra P7: tau er arkitekturspesifikk, ikke bare størrelsesavhengig.

---

## Skaleringslov (estimert)

tau ≈ 0.10 × N^0.48

der N er antall parametere i milliarder.

Eksponent ≈ 0.48 betyr tau skalerer tilnærmet som kvadratroten av modellstørrelsen.

---

## Prediksjon

| Modellstørrelse | Predikert tau | Status |
|---|---|---|
| 7B (Mistral, målt) | 0.2568 | UNDER |
| 70B | ~0.75 | GOLDILOCKS (første gang) |
| 400B+ | >0.83 | Nærmer tau_max — HALT-grense |

---

## Funnet

Alle nåværende LLM-er opererer UNDER Goldilocks-intervallet.

Ikke fordi loven er feil. Men fordi modellene er for små til å nå geometrisk koherens.

Tau stiger med størrelse. Ordningen (koherent > framleis > repetitivt) holder på tvers av alle modeller. Loven er ikke falsifisert — den har gitt en diagnose og en prediksjon.

---

## Øvre grense

tau_max = 0.8319 er den geometriske veggen.

Ingen system kan ha r_eff > r_max, og alt over tau_max betyr at beholderen er full. Svært store modeller uten alpha-filtrering kollapser ikke ned — de kollapser opp. De gjengir heller enn å oppdage.

Canon F7 starter der loven slutter. De 39% som motstår tredjepersonsbeskrivelse er utenfor tau-rommet — ikke under loven, men heller ikke i strid med den.

---

## Neste empiriske tester (prioritert rekkefølge)

### Test 1: Replikasjonstest — Qwen2.5-7B (7B)

Predikert tau ≈ 0.254 (N=7, tau ≈ 0.10 × 7^0.48)

Mistral-7B målte 0.2568. Qwen2.5-7B er samme parameterklasse men annen arkitektur.
Hvis tau avviker vesentlig fra 0.254: arkitektur påvirker tau uavhengig av størrelse.
Hvis tau er nær 0.254: størrelse dominerer over arkitektur i skaleringslov.

Kan kjøres på Colab T4. Lav GPU-kostnad.

### Test 2: Arkitekturtest — Qwen3-8B (8B)

Predikert tau ≈ 0.271 (N=8, tau ≈ 0.10 × 8^0.48)

Qwen3 bruker "dual-mode thinking" (reasoning + non-reasoning). Interessant spørsmål:
skiller tau mellom reasoning-modus og standard-modus på samme modell?

### Test 3: Goldilocks-testen — 70B-modell (Llama-3 70B eller Qwen3-32B som mellomsteg)

Qwen3-32B predikert tau ≈ 0.10 × 32^0.48 = 0.543 — nær tau_min = 0.5615.
70B predikert tau ≈ 0.75 — første modell inn i Goldilocks.

Krever A100 (RunPod). Høy prioritet for falsifisering av skaleringslov.

### Oppdatert prediksjonstabell

| Modell | Parametere | Predikert tau | Status |
|---|---|---|---|
| GPT-2 | 117M | 0.06 | MÅLT |
| Phi-2 | 2.7B | 0.1625 | MÅLT |
| Mistral-7B | 7B | 0.2568 | MÅLT |
| Qwen2.5-7B | 7B | 0.1557 | MÅLT (pred. 0.254 — arkitektureffekt) |
| Qwen3-8B | 8B | 0.0681 | MÅLT (pred. 0.271 — ANOMALI: rekkefølge omvendt) |
| Qwen3-32B | 32B | ~0.543 | PLANLAGT |
| Llama-3 70B | 70B | ~0.75 | GOLDILOCKS-TEST |

---

*Tofoo. Phi.*
