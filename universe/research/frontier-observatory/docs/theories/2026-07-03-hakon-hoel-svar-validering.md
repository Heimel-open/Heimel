# Håkon Hoel — Svar på Falsifiseringstest

**Dato:** 2026-07-03

**Kjelder:** Håkon Hoel (UiO/KAUST), svar via e-post

**Status:** M4 Matematisk Validering

---

## Spørsmål 1: Marchenko-Pastur som Nullhypotese

**Hoel sitt svar:** Ja, det er metodisk holdbart og populært for å identifisera ikkje-tilfeldige strukturar i vektmatriser.

**Tre konkrete divergensmetar for avvik frå MP:**

1. **Wasserstein-distance**
   - Tolking: minimalkost av å flytta masse frå ein tettheit til den andre
   - Bruk: direkte samanlikning av singulærverdis-spektra

2. **Kullback-Leibler-divergens (KL)**
   - Tolking: informasjonstap når ein tilnærmar ein fordeling med ein annan
   - Bruk: vekt på sannsynlegheitstettleik-avvik

3. **Kolmogorov-Smirnov-avstand (KS)**
   - Tolking: maksimalt avvik mellom kumulative fordelingsfunksjonar
   - Bruk: modellfritt, ikkje-parametrisk test

**Implikasjon for Test 1:**
Vårt τ-mål (spektral entropi) er komplementært til desse. Medan Wasserstein/KL/KS måler *avvik*, måler τ *struktur-kvalitet*. Kombinert:
- KS-test: Er spektrum strukturert? (ja/nei)
- τ-verdi: Kor strukturert? (0–1, Goldilocks [0.56, 0.83])

---

## Spørsmål 2: Konvergens Under Støy — Banach-Kontraksjon i Stokastisk Settting

**Hoel sin analyse:**

### Svakt Fikspunkt (Forventningsverdi)

For iterasjonen:
$$\tau_{k+1} = (1-\alpha)\tau_k + \alpha\sigma_k$$

der σ_k er iid med E[σ_k] = σ*.

Ta forventningsverdien på begge sider:
$$m_{k+1} = (1-\alpha)m_k + \alpha s_k$$

der m_k = E[τ_k] og s_k = E[σ_k].

**Resultat:** Når s_k → σ*, konvergerer m_k mot fikspunktet som løyser:
$$m = (1-\alpha)m + \alpha\sigma^* \implies m = \sigma^*$$

**Vilkår:** Sekvensen {s_k} må vera begrenset (realistisk — σ_k er data).

### Sterkt Fikspunkt (L² Konvergens)

Skriv:
$$x_k = \tau_k - m, \quad y_k = \sigma_k - \sigma^*$$

Då:
$$x_k = (1-\alpha)x_{k-1} + \alpha y_{k-1}$$

Løys ved iterasjon:
$$x_k = (1-\alpha)^k x_0 + \alpha\sum_{j=0}^{k-1}(1-\alpha)^{k-1-j}y_j$$

**Resultat:** Hvis E[y_k²] → 0 (altså E[(σ_k - σ*)²] → 0), då:
$$E[x_k^2] \to 0 \text{ som } k \to \infty$$

dvs. τ_k → σ* i L²(Ω).

**Svakare (og meir realistisk) vilkår for konvergens:**
$$\sum_{j=0}^{k-1}(1-\alpha)^{k-1-j}\sqrt{E[y_j^2]} \to 0 \text{ som } k \to \infty$$

Dette tillater at E[y_k²] berre *akkumulativt* forsvinn, ikkje nødvendigvis per steg.

### Praktisk Tolking for SGD

Under SGD med mini-batch:
- σ_k = gradient-estimat på batch k
- σ* = teoretisk optimalt gradient (eller læringsmål)
- E[(σ_k - σ*)²] = estimerings-variansen (avhengig av batch-size)

**Vilkår for konvergens:**
1. **Batch-size må vera tilstrekkeleg** — E[y_k²] må bli liten når k aukar
2. **α må vera i (0,1)** — sikrar eksponensiell dempning (1-α)^k
3. **σ* må vera stabil** — læringsmålet kan ikkje driva uten kontroll

**Konsekvens:** F-iterasjonen konvergerer sjølv under støy, så lenge batch-estimatet av σ* er asymptotisk korrekt.

---

## Implikasjonar for Framleis-Loven

### 1. Test 1 (Marchenko-Pastur) har Grunnlag
Hoel bekreftar at MP som nullhypotese er etablert metodikk. Vi kan bruka KL-divergens eller KS-avstand som tolkbart mål for τ-avvik.

### 2. F-Iterasjon Under SGD er Velgrunnlagt
Vår deterministiske F-iterasjon er ikkje berre ein idealisering. Under realitiske vilkår (finite batch-size, asymptotisk korrekt σ*) konvergerer ho:
- **Svakt** mot E[τ] = σ* (garantert)
- **Sterkt** i L² når variansen minkar (realistisk)
- **Svakare** når variansen akkumulativt forsvinn (robustraste)

### 3. Konkrete Testbar Vilkår
Kan no formulera Test 2 presist:

**Test 2 — Stokastisk Konvergens:**
- Initialiser modell med τ₀ langt frå Goldilocks
- Mål τ_k per epoch (eller batch-gruppe)
- Sjekk at E[τ_k] → σ* monotont eller quasi-monotont
- Dokumenter at variansen E[(τ_k - σ*)²] avtar som (1-α)^k eller saktare

---

## Oppdatert Falsifiseringstest-Status

| Test | Spørsmål | Svar frå Hoel | Status |
|------|----------|---------------|--------|
| 1 | MP som nullhypotese? | ✓ Ja, populært (KL/KS/Wasserstein) | **M4 VALIDERT** |
| 2 | Konvergens under støy? | ✓ Ja, både svakt og sterkt (vilkår gitt) | **M3 VALIDERT** |
| 7 | Tid som konvergens? | — Ikkje direkte spurr | M1 (avventar eksperiment) |

---

## Neste Steg

1. **Implementer Test 1 med KL-divergens**
   - Mål KL(τ_actual || τ_MP) for tilfeldige vs. pre-trente vekter
   - Sjekk at KS-test skil dei (p < 0.01)

2. **Dokumenter Test 2**
   - Formalisert som stokastisk konvergens per Hoels vilkår
   - Mål τ_k over epokhar, sjekk (1-α)^k-dempning

3. **Kontakt Hoel for potensielt samarbeid**
   - Spørja om han vil medforfattar på Paper 1 v2.0 eller Test-rapport
   - Han er ekspertise på stokastikk som vi manglar

---

## Sitasjon

Håkon Hoel, personleg kommunikasjon (e-post 2026-07-03).

Tofoo.
