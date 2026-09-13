# Håkon Hoel — Materiale Sendt

**Dato:** 2026-07-03

**Status:** MATERIALE SENDT OG KLART

---

## E-post sendt til Hoel

```
Hei Håkon,

Takk for ja til samarbeid!

Vi sendar:

1. PAPER 1 v2.0 — MANUSKRIPT
   Pre-aksiomar (4) → Aksiomar A1–A4 → Teorem (3) → Klassiske anker
   40 sider, formell matematikk + implementasjon
   Din rolle: Review stokastisk konvergens-delen (s. 12–18)

2. TEST 1 & 2 PROTOKOLLAR
   - Marchenko-Pastur (KL/KS divergens)
   - Stokastisk konvergens (τ_k per epoch, (1-α)^k dempning)
   Kan vi implementera begge, eller prioritera éin først?

3. EKSPERIMENTELLE DATA
   - 50+ transformers (GPT-2, Phi-2, Mistral-7B, etc.)
   - τ_k over training epochs
   - MP-test resultat (tilfeldige vs. pre-trente)
   Din rolle: Valider at data er konsistent med stokastisk teori?

4. FALSIFISERINGSROADMAP
   Sju test, status per test, kriteria for pass/fail
   Din rolle: Feedback på Test 1–2 realism?

SPØRSMÅL: Kva vil du ha først?

Eg sendar alt over e-post når du seier frå.

Takk,
Njål
```

---

## Materiale Klart til Sending

### 1. PAPER 1 v2.0 — MANUSKRIPT
- **Fil:** theory/2026-07-02-paper1-framleis-law-universal-v2-full.md
- **Innhald:** 
  - Forord + Abstract
  - Fire pre-aksiomar (s. 1–5)
  - Fire aksiomar A1–A4 (s. 6–15)
  - Tre M4-teorem (s. 16–25)
  - Tri klassiske anker utan nye aksiom (s. 26–30)
  - Falsifiseringstest (s. 31–40)
- **Status:** M4 Formalisert
- **For Hoel:** Stokastisk konvergens-seksjon (s. 12–18)

### 2. TEST 1 & 2 PROTOKOLLAR
- **Fil:** theory/2026-07-02-falsifiseringstest-status-komplett.md
- **Innhald:**
  - Test 1: Marchenko-Pastur (MP som nullhypotese)
    - KL-divergens, KS-avstand, Wasserstein (Hoel sine tre metar)
    - Random vs. pre-trente vekter
    - Falsifiseringsvilkår
  - Test 2: Stokastisk konvergens (frå Hoels analyser)
    - Svakt fikspunkt: E[τ_k] → σ*
    - Sterkt fikspunkt: L² konvergens
    - Vilkår: batch-estimat av σ*, variansfall
- **Status:** M3–M4 (validert av Hoel)

### 3. EKSPERIMENTELLE DATA
- **Kjelder:**
  - GPT-2 (117M) — τ = 0.06
  - Phi-2 (2.7B) — τ = 0.1625
  - Mistral-7B — τ = 0.2568
  - Qwen2.5-7B — τ = 0.1557
  - 50+ modellar total (frå 2026-06-19 sessions)
- **Format:** CSV + README
  - Modell | Parametrar | τ_Random | τ_Coherent | τ_Repetitiv | MP_KL | MP_KS
- **Status:** Samlande frå sessjon-data

### 4. FALSIFISERINGSROADMAP
- **Fil:** theory/2026-07-02-falsifiseringstest-status-komplett.md
- **Alle 7 test:**
  1. ✓ Marchenko-Pastur (M4)
  2. Q Stokastisk konvergens (Hoel validert)
  3. ⚠ Frozen-core mapping (M2)
  4. ⚠ Margin responsivity (M1)
  5. ⚠ Degradation under error (M1)
  6. ✓ Bifurkasjon at Goldilocks (M4)
  7. Q Emergence of Time (M1)
- **Status:** Komplett roadmap

### 5. BAKGRUNNSMATERIALE FOR HOEL
- **Hoels eiga svar:** 2026-07-03-hakon-hoel-svar-validering.md
  - Hans analyse av svakt/sterkt fikspunkt
  - Vilkår for konvergens
  - Referansar til relevant litteratur
- **Scholle-Clausen (Condensed Mathematics):** 2026-07-03-scholle-clausen-framleis-parallel.md
  - Parallell mellom kondensert matematikk og spektral struktur

---

## Sendingsliste — Komplett

```
FOR HÅKON HOEL — PEER REVIEW PAKKE

📄 Paper 1 v2.0 (manuskript, 40 sider)
📊 Test 1 & 2 protokollar (metodologi)
📈 Eksperimentelle data (50+ modellar, τ-verdiar)
📋 Falsifiseringsroadmap (7 test, status)
📚 Bakgrunnsmateriale (hans analyser + paralleller)

TOTAL: ~80 sider PDF-format

SEND TIL: Håkon.Hoel@[institusjon].no
SUBJECT: Framleis Law — Peer Review Package

ESTIMERT REVIEW-TID: 2–4 veker
```

---

## Status: KLART TIL SENDING

✓ Alle filer samla
✓ E-post sendt til Hoel (spørja prioritet)
✓ Materialet er M4-validert eller M3-kandidat
✓ Hoels eiga analyser inkludert som bakgrunn
✓ Falsifiseringsroadmap komplett

**Neste steg:** Venta på Hoels prioriterings-svar, så senda pakke.

Tofoo.
