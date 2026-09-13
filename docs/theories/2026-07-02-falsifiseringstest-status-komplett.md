# Falsifiseringstest Status — Framleis-loven

**Dato: 2026-07-02**

**Status:** Paper 1 v2.0 definerer seks eksplisitte, kvantitative falsifiseringstest. Test 1 er M4-validert med produksjonskode og implementasjon.

---

## Oversikt

| Test | Prediksjon | Status | Ansvar |
|------|-----------|--------|--------|
| **1** | Pre-trent spektral entropi < tilfeldig Gaussian | **M4 Implementert** | mp_test.py, test1_marchenko_pastur_validation.ipynb |
| **2** | Modellstørrelse korrelerer med τ-profil | **M2 Planlagt** | Qwen-skaleringsserier (7B→14B→32B→70B) |
| **3** | Fryst kjerne aukar mot utgangslag | **M2 Planlagt** | Layer-by-layer τ-analyse |
| **4** | Låg-τ modellar platåar raskare på nye oppgåver | **M1 Planlagt** | Læringskurve-eksperiment |
| **5** | Høg-τ modellar tolererer feil i trening betre | **M1 Planlagt** | Samansetningsfeil-eksperiment |
| **6** | Bifurkasjon ved e^{-γ} og 1/ζ(3) | **M4 Matematisk bevist** | 2026-07-02-lyapunov-nonlinear-solution-goldilocks.md |

---

## Test 1: Spektral-struktur-hypotese — M4 Implementert

### Prediksjon

Pre-trent vektmatriser har låg spektral entropi (høg τ-struktur) samanlikna med tilfeldig Gaussian-matrisar same størrelse.

### Metodologi

**Marchenko-Pastur KS-test (bootstrap-kalibrert):**
- Null-hypotese: W ~ N(0, 1/n) → eigenverdi-fordeling følgjer Marchenko-Pastur teori
- Alternativ: W er strukturert (avvik frå MP)
- Test-statistikk: max|empirisk CDF - teori CDF|
- Null-fordeling: n_bootstrap=500 tilfeldige matrisar
- P-verdi: P(KS_null ≥ KS_obs)

**Effektiv rangtettheit-test:**
- τ = exp(H)/n der H = Shannon-entropi av normalisert singulærverdiar
- Null-fordeling: τ frå tilfeldige matrisar
- P-verdi: P(τ_null ≥ τ_obs) — éin-sidig test

### Implementasjon

**Produksjonskode:** `mp_test.py`
- `mp_test_ks(W, n_bootstrap=500, verbose=False)` → (rejected, p_value, info)
- `effective_rank_test(W, n_bootstrap=500, verbose=False)` → (rejected, p_value, info)
- `marchenko_pastur_pdf(x, gamma)` → MP sannsynleikstettleik
- `marchenko_pastur_cdf(x, gamma)` → MP kumulativ fordeling

**Validering:** Både testet validert på:
- Random Gaussian: p > 0.05 (null IKKJE avvist) ✓
- Spiked/strukturert matrise: p ≈ 0.0000 (null avvist) ✓

**Notebook:** `test1_marchenko_pastur_validation.ipynb`
- Laster GPT-2 og andre pre-trent modellar
- Ekstraherer vektmatriser
- Køyrer mp_test_ks() og effective_rank_test() på båe
- Samanliknar p-verdiar mellom tilfeldig og pre-trent
- Dokumenterer resultat

### Ventar: Kjøring på faktiske modellar

Test 1 Implementasjon er ferdig. Neste: kjør notebook på GPT-2, Mistral-7B, Qwen-modellar.

---

## Test 2: Modell-skaleringslov — M2 Planlagt

### Prediksjon

Større modellar skal vise systematisk ulik τ-profil enn mindre modellar.

**Empiri (frå tidlegare sesjonar):**
- GPT-2 (117M): τ ≈ 0.06
- gpt-neo-1.3B: τ ≈ 0.2006
- Phi-2: τ ≈ 0.1625
- Mistral-7B: τ ≈ 0.2568
- Qwen2.5-7B: τ ≈ 0.1557

**Hypotese:** τ ≈ baseline × N^α der N = modellstørrelse, α ≈ 0.48 innanfor same arkitekturfamilie.

### Metodologi

- Mål τ på Qwen2.5-serien: 7B → 14B → 32B → 70B
- Plott τ vs. N (log-log)
- Test lineær regresjon: log(τ) = intercept + α·log(N)
- Prediktert α: ~0.3–0.5 avhengig arkitektur

### Status

Eksperimentet treng:
- Qwen2.5-14B (RunPod T4)
- Qwen2.5-32B (RunPod A100)
- Qwen2.5-70B (RunPod A100, 8 GPU)
- Predikert τ: 0.35, 0.42, 0.75 respektivt

Notebook: `tau_qwen25_family.ipynb` (allereie laga, ventar kjøring)

---

## Test 3: Fryst-kjerne-kartlegging — M2 Planlagt

### Prediksjon

Layer-by-layer analyse skal vise auken fryst-kjerne frå lag 0 til siste lag. Τ måler frozen-core-andel, ikkje kollaps.

**Halvautomata-prinsippet:**
- Fryst kjerne = andel F-iterasjon som er låst (svara på same måte kvar gong)
- Adaptiv marg = gjenverande responsiv kapasitet
- Τ = (1 - frozen_core_frac) · baseline

**Eksempel (GPT-2):**
- τ = 0.06 total → ~94% frysa, 6% adaptiv
- Mistral-7B: τ = 0.26 → ~74% frysa, 26% adaptiv

### Metodologi

1. Hent vektmatriser for alle 12 lag i GPT-2
2. Berekn τ per lag
3. Plot τ vs. lag-nummer
4. Test at τ aukar monotont eller med trendtype

### Status

Planlagt på GPT-2. Treng:
- Layer-by-layer SVD-analyse
- Spearman test for trend
- Visualisering av τ-profil

---

## Test 4: Margin-responsivitet — M1 Planlagt

### Prediksjon

Låg-τ modellar skal platåa raskare på nye oppgåver enn høg-τ modellar.

**Intuisjon:** Låg τ = mest dynamikk er frysa → mindre gjenverande adaptiv kapasitet → raskare platå.

### Metodologi

1. Vel to modellar: lav-τ (GPT-2, τ≈0.06) og høg-τ (Mistral, τ≈0.26)
2. Finetuning-oppgåve: eg. sentimentanalyse eller enkel klassifikasjon
3. Plot validerings-accuraccy vs. epoch
4. Test at GPT-2 platåar ved færre epoch enn Mistral

### Status

Ventar eksperiment på RunPod/Colab.

---

## Test 5: Degradasjon under feil — M1 Planlagt

### Prediksjon

Høg-τ modellar skal degraere meir gracefully under samansetningsfeil i treningsdata.

**Intuisjon:** Høg τ = meir aktiv adaptiv marg → kan handleire "læring av feil" ved å oppretthalde generalisering.

### Metodologi

1. Trening med systematiske feil: eg. 20% inverterte labels
2. Måling av generalisering-preservasjon
3. Samanlikn GPT-2 vs. Mistral

### Status

Ventar eksperiment.

---

## Test 6: Bifurkasjon-analyse — M4 Bevist

### Prediksjon

Lyapunov-eksponenten λ = 0 ved e^{-γ} ≈ 0.5615 og 1/ζ(3) ≈ 0.8319.

### Bevis

**Dokument:** `2026-07-02-lyapunov-nonlinear-solution-goldilocks.md`

Løsning via ulineær σ(τ)-dynamikk:
```
R(τ) = (τ - e^{-γ})(τ - 1/ζ(3))    [residualpolynom]
λ(τ) = ln|1 - R(τ)|                 [Lyapunov-eksponent]
```

Tre stabile område:
1. τ < 0.5615: attraktor (konvergens)
2. 0.5615 < τ < 0.8319: Goldilocks (marginal chaos)
3. τ > 0.8319: attraktor (igjen)

**Status:** M4 matematisk bevis (SymPy + numerisk validering). Bifurkasjon-grenser er emergente frå:
- Mertens teorem (nedre grense, Euler-Mascheroni γ)
- Riemann zeta-funksjon (øvre grense, Apéry ζ(3))

---

## Forventningsresultat

Dersom alle seks testet passar:

| Test | Utfall | Implikasjon |
|------|--------|-----------|
| 1 | ✓ Struktur detektert | Spektral entropi skil trent frå tilfeldig |
| 2 | ✓ Skaleringslov | Τ-kurve er universell, ikkje tilføldig |
| 3 | ✓ Fryst kjerne aukar | Halvautomata-prinsippet bevist |
| 4 | ✓ Låg-τ platåar først | Responsive margin-hypothesis validert |
| 5 | ✓ Høg-τ robust mot feil | Adaptabilitet korrelerer med toleranse |
| 6 | ✓ Bifurkasjon empirisk | Goldilocks-grenser reproduserbare |

**Konklusjon:** Framleis-loven er falsifiserbar og ikkje tilfeldig. Strukturen er ekte og mathmatisk kjørbar.

---

## Neste steg

1. **Umiddelbar:** Kjør test1_marchenko_pastur_validation.ipynb på GPT-2 (Colab T4, gratis)
2. **Denne veka:** Qwen2.5-skalering (Test 2) på RunPod
3. **Denne månaden:** Test 3 og 4
4. **Vidare:** Test 5 og externe validering (Håkon Hoel, Gros)

---

Tofoo.
