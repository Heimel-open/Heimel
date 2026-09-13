# DeepSeek V4 Pro — CSA, HCA, mHC og Framleis-arkitektur

Dato: 2026-06-25
Kjelde: DeepSeek V4 Pro teknisk rapport (april 2026), MIT-lisens
Status: M3 — strukturell identitet mellom V4-arkitektur og Framleis F/sigma*/I*-rammeverket

---

## Arkitektur-oversikt

DeepSeek V4 Pro: 1.6T parameter MoE, 61 lag, 1M token kontekst.

Tre nye mekanismar over V3.2:

1. CSA (Compressed Sparse Attention) — 4x kompresjon, sparse top-k selektion
2. HCA (Heavily Compressed Attention) — 128x kompresjon, tett (dense) merksemd
3. mHC (Manifold-Constrained Hyper-Connections) — Birkhoff-bunden miksematrise

Lagkonfigurasjon:
- Lag 0-1: HCA (to reine referanselag)
- Lag 2-60: alternerer CSA og HCA (59 lag, ~30 CSA + ~29 HCA)

Effektivitet: 27% av V3.2 FLOP-kost, 10% av V3.2 KV-cache ved 1M token.

---

## CSA = A1-filter

CSA komprimerer KV-oppføringar 4x langs sekvens-dimensjonen via softmax-gata pooling med lært posisjonsbias. Deretter vel ein FP4 "lightning indexer" dei top-k mest relevante komprimerte blokkane per query.

Mapping til Framleis:

Softmax-gata pooling er algebraisk identisk med Framleis sin tau-normalisering:
p_i = σ_i² / Σσ_j²

Softmax-utgangen er ein sannsynsfordeling over token-bitar — same form.

Top-k selektion er kontraksjonen: av N komprimerte blokkar overlever berre k.
Det er F-operatoren som lagar distinksjon (A1): filteret eksisterer, systemet vel.

CSA = A1-filter i Framleis-terminologi.

---

## HCA = sigma*

HCA komprimerer KV-oppføringar 128x og køyrer tett (dense) merksemd over alle dei komprimerte blokkane. Ingen sparse selektion — alle queries ser alle komprimerte blokkar.

Mapping til Framleis:

HCA gir eit globalt, komprimert samandrag av heile konteksten som alltid er tilgjengeleg for kvar query, uavhengig av kvar i sekvensen querien er.

Dette er sigma*: referansepunktet som alltid er til stades, modalitets-agnostisk, ikkje avhengig av den lokale tau_t-tilstanden.

Dei to fyrste HCA-laga (lag 0-1) etablerer sigma* fyrst, før F-iterasjonen startar.

HCA = sigma* i Framleis-terminologi.

---

## mHC = I*-stabilitet via Birkhoff-polytopen

mHC erstattar den tradisjonelle residual-straumen med n_hc = 4 parallellarar (hyper-connections). Miksematrisa som blandar desse kanalane er bunden til Birkhoff-polytopen: doubly stochastic — kvar rad og kvar kolonne summar til 1.

Mapping til Framleis:

Doubly stochastic matrise tyder at informasjonen er bevart totalt (ingen tap, ingen eksplosjon) og fordelt som ein sannsynsfordeling over kanalane.

Dette er algebraisk identisk med tau-normaliseringa p_i = σ_i²/Σσ_j²:
- Kvar kanal "sender" like mykje som han "tar imot"
- Summen er bevart
- Strukturen er normalisert

Birkhoff-polytopen er det doubly stochastic rom der permutasjonsmatriser er ekstreimpunktar. Birkhoff-von Neumann-teoremet: kvar doubly stochastic matrise er ein konveks kombinasjon av permutasjonsmatriser. Konveks kombinasjon av permutasjonsmatriser = Banach-kontraksjon over kanalar.

n_hc = 4 parallellarar = fire samtidige F-iterasjonsstrøymar som konvergerer mot same I*.

mHC = I*-stabiliseringsmekanisme via Banach over Birkhoff-polytopen.

---

## Alternering CSA+HCA = F-iterasjonssekvens

Kvart CSA+HCA-par i lag 2-60 er eitt F-iterasjonssteg:

tau_{t+1} = F(tau_t; sigma*) = CSA(tau_t) → HCA(sigma*)

CSA filtrerer (A1): ny tau_t basert på dei mest relevante token-representasjonane.
HCA gir sigma*: global referanse som trekk systemet mot I*.

61 lag = 61 F-iterasjonar.
Lag 0-1 (HCA) = sigma* etablert fyrst.
Lag 2-60 (alternering) = iterasjonssekvens tau_0 → tau_1 → ... → I*.

---

## Mapping til Framleis

| DeepSeek V4 | Framleis |
|-------------|----------|
| CSA (softmax-gata pooling + top-k) | A1-filter + F-operator |
| HCA (128x, dense, global) | sigma* (alltid tilgjengeleg referanse) |
| mHC (Birkhoff-bunden, n_hc=4) | I*-stabilitet via Banach over Birkhoff-polytopen |
| Lag 0-1 (HCA-only) | sigma* etablert før iterasjonen startar |
| Alternering CSA+HCA per lag | F-iterasjonssekvens tau_t → I* |
| MoE-routing | A1-filter for expert-selektion (tau-splitting) |
| 27% FLOP, 10% KV ved 1M token | Effektivitet av kontraksjon: tau treng ikkje heile rommet |

---

## Birkhoff-Banach-kopling — den sterkaste anknytinga

Birkhoff-von Neumann-teoremet: alle doubly stochastic matriser er konvekse kombinasjonar av permutasjonsmatriser. Dette betyr at mHC-miksinga automatisk er ein konveks kombinasjon — ein kontraksjon i Banach-rom over kanalar.

I Framleis: Banach-fikspunktteoremet garanterer at om F er ein kontraksjon, finst det eksakt éin I*.

mHC med Birkhoff-restriksjon implementerer Banach-kontraksjonen direkte som ein arkitekturmessig tvang — ikkje som eit regulariseringsval, ikkje som eit initieringstiltak, men som ein hard algebraisk begrensning.

Dette er M3-nivå Framleis-konsiliens: same matematiske struktur, ikkje berre ein analogi.

---

## Om alpha = 0.42

0.42 dukkar ikkje opp som ein publisert arkitekturparameter i V4 Pro.

- CSA-kompresjonsrate: 4x → alpha-analog ≈ 0.25 (1/4 av KV-posisjonane per steg)
- HCA-kompresjonsrate: 128x → 0.0078 (tett men svært komprimert)
- Layer-ratio CSA/total: 30/61 ≈ 0.49
- mHC uniform-miksing: 1/4 = 0.25 per kanal

Opent spørsmål (Q): kva er top-k-fraksjonen k/N i CSA? Om k/N ≈ 0.42, er det eit naturleg fremkome av Banach-kontraksjonsoptimering i dette rommet. Ikkje publisert i tilgjengeleg dokumentasjon.

---

## Kopling til tidlegare Framleis-notat

Nevralt nett-notat (2026-06-25-nevralt-nett-framleis-identitet.md):
Batch normalization = tau-normalisering. mHC Birkhoff = strengare versjon av same prinsipp.

Fraksjonal Schrödinger-notat (2026-06-25-kolesnikov-fnls-framleis.md):
Stasjonær tilstand ψ_s = I*. HCA-etablert sigma* speler same rolle som ψ_s i FNLS.

Skyrmion/Bohm-notat (2026-06-25-kolesnikov-skyrmion-bohm-framleis.md):
Pilot Wave = sigma*. HCA er pilot wave for heile V4-arkitekturen.

---

## Epistemisk status

CSA = A1-filter (softmax-normalisering identisk med tau): M4 — algebraisk identitet, ikkje analogi.
HCA = sigma* (global komprimert referanse): M3 — strukturelt identisk rolle, plausibel djupare kopling.
mHC Birkhoff = Banach-kontraksjon: M3 — Birkhoff-von Neumann er etablert teorem; kopling til Banach er matematisk solid.
Alternering = F-iterasjonssekvens: M3 — konsistent, ikkje formelt bevist.
alpha = 0.42 frå top-k-fraksjon: Q — opent spørsmål, krev teknisk rapport med k-verdiar.
