# Birkhoff-polytopen, Sinkformer-familien og tau-kollaps

Dato: 2026-06-25
Kjelde: Sinkformers (2021), QDSFormer (NeurIPS 2025, IBM), ESPFormer (2025), LOTFormer (2025), Sinkhorn rank decay analysis (arXiv 2604.07925, april 2026), mHC/go-mHC (Xie et al. 2026)
Status: M3 — empirisk og teoretisk konsiliens med Framleis tau-kollaps-prediksjon

---

## Hovudfunnet

Ei heil forskningslinje (2021–2026) konvergerer mot doubly stochastic merksemd (DS-attention) som eit grunnleggjande prinsipp i transformerar. Den felles matematiske strukturen er Birkhoff-polytopen — mengda av alle doubly stochastic matriser.

Framleis predikerer dette: doubly stochastic normalisering = tau-normalisering over både rader og kolonnar. Det er den algebraiske strukturen som gjer at I* er stabil.

---

## Sinkformer-familien (kronologisk)

Sinkformers (2021) — den originale artikkelen. Normaliserer merksemd-matrisa med Sinkhorn-algoritmen (iterativ rad-kolonne-normalisering) i staden for standard softmax (rad-normalisering åleine). Resultat: konsistent forbetring på tvers av domene.

QDSFormer (NeurIPS 2025, IBM Research) — kvantum-indusert doubly stochastic merksemd. Estimerer parametrisk, kan lærast til vilkårlege transformasjonar på Birkhoff-polytopen. Meta-klasse av Sinkformers.

ESPFormer (2025) — doubly stochastic merksemd via Expected Sliced Transport Plans (knytt til Wasserstein-geometri).

LOTFormer (2025) — lineær DS-merksemd via låg-rang optimaltransport. Samanliknbar med Sinkformer og ESPFormer.

mHC i DeepSeek V4 (Xie et al. 2026) — Birkhoff-bundna hyper-connections som erstattar residual-straumen. n_hc=4, ikkje DS-merksemd men DS-miksing over kanalane.

go-mHC (arXiv 2604.02309) — generalisert ortostokastisk parametrisering av mHC. Matematisk presisering av korleis Birkhoff-polytopen implementerast effektivt.

---

## Rank decay-analysen: formell bevis for tau → 0

Lapenna et al. (arXiv 2604.07925, april 2026) viser:

- Standard softmax-merksemd: ranken av merksemd-matrisa kollapsar doubly eksponentielt med djupna → uniform representasjon → tau → 0
- Doubly stochastic Sinkhorn-merksemd: same doubly eksponentielle rangkollaps
- Skip connections er avgjerande for å hindre kollaps

I Framleis:

Rangkollaps = tau → 0 (singulærverdi-spektret kollapsar til rang 1, alle token-representasjonar blir like).
Doubly eksponentielt = tau_t = tau_0^(2^t) for t lag — utan F-iterasjon (skip connection) er kollapsen ikkje berre gradvis, han akselererer.

Dette er ei formell stadfesting av Framleis-prediksjonen: utan F-operatoren kollapsar tau_t eksponentielt.
Og det forklarer kvifor mHC (Birkhoff-bunden skip connection) er nødvendig: han er den F-operatoren som hindrar kollapsen.

---

## Birkhoff-Banach-koblingen som felles kjerne

Birkhoff-von Neumann-teoremet: alle doubly stochastic matriser er konvekse kombinasjonar av permutasjonsmatriser (ekstreimpunktane på polytopen).

Konveks kombinasjon av permutasjonsmatriser er ikkje-ekspansiv (normbevarande).
Ikkje-ekspansiv = Banach-kontraksjon med faktor ≤ 1.

I Framleis: Banach-fikspunktteoremet krev kontraksjon. Birkhoff-polytopen implementerer dette geometrisk.

Alle modellane i Sinkformer-familien, og mHC i DeepSeek V4, implementerer den same Banach-kontraksjonen — via ulike mekanismar men same algebraiske struktur.

---

## Optimal transport-koblingen

DS-merksemd er algebraisk identisk med ein optimal transport-plan (Wasserstein-avstand).

I optimal transport: ein doubly stochastic matrise P_{ij} seier kor mykje "masse" som vert flytta frå posisjon i til posisjon j. Minimering av transportkost = Wasserstein-avstand = Framleis F-operator som minimerer avstanden mellom tau_t og sigma*.

ESPFormer og LOTFormer gjer denne koplingen eksplisitt. Merksemd-matrisene er optimaltransport-planar.

I Framleis: F(tau; sigma*) minimerer avstandan mellom tau_t og sigma*. Optimal transport er det same minimeringsproblemet i kontinuerleg form.

---

## Mapping til Framleis

| Sinkformer-familie | Framleis |
|-------------------|-----------|
| Birkhoff-polytopen | Banach-rom der F er kontraksjon |
| Doubly stochastic normalisering | tau-normalisering over rader (token) OG kolonnar (posisjon) |
| Sinkhorn-iterasjon (rad→kolonne→rad→...) | F-iterasjonssekvens mot sigma* |
| Rangkollaps utan skip connections | tau → 0 utan F-operator |
| Skip connections / mHC | F-operatoren som hindrar tau → 0 |
| DS-matrise som optimaltransport-plan | F-operator som minimerer avstand til sigma* |
| Doubly eksponentielt rangfall | tau_t = tau_0^(2^t) utan kontraksjon |

---

## Prediksjon: Sinkhorn-iterasjonen er ein Framleis-subsystem

Sinkhorn-algoritmen itererer: normaliser rader → normaliser kolonnar → normaliser rader → ...

I Framleis: tau_{t+1} = F(tau_t; sigma*) = (1-alpha)*tau_t + alpha*sigma*

Sinkhorn-iterasjonen er ein spesiell F-operasjon der sigma* = uniform fordeling (1/n per oppføring) og alpha = 1 (full erstatning per steg). Fikspunktet er den doubly stochastic matrisa som minimerer KL-divergens frå utgangspunktet.

Prediksjon: tau(merksemd-matrise) normaliserer seg mot Goldilocks-sona etter Sinkhorn-konvergens. Testbar via spektral entropi av den DS-normaliserte merksemd-matrisa.

---

## Kopling til tidlegare Framleis-notat

DeepSeek V4-notat (2026-06-25-deepseek-v4-csa-hca-mhc-framleis.md):
mHC er Birkhoff-implementasjonen i produksjonsskala. Dette notatet gir det matematiske grunnlaget.

Nevralt nett-notat (2026-06-25-nevralt-nett-framleis-identitet.md):
Batch normalization = tau-normalisering per lag. DS-normalisering = tau-normalisering i to dimensjonar samstundes.

Kvadrat-topologisk-kode-notat (2026-06-22-kvadrat-topologisk-kode-tau.md):
p_i = σ_i²/Σσ_j² er rad-normalisering. DS-matrise = p_i,j / Σ_{i,j} = normalisering i begge dimensjonar.

---

## Epistemisk status

Doubly stochastic normalisering = tau-normalisering over to dimensjonar: M4 — algebraisk identitet.
Birkhoff-von Neumann = Banach-kontraksjon: M4 — etablert teorem.
Rangkollaps utan F-operator = tau → 0: M4 — formelt bevist i Lapenna et al. 2026.
Sinkhorn-iterasjon = Framleis-subsystem: M3 — strukturelt identisk, ikkje formelt identisk.
Optimal transport = F-minimering av avstand til sigma*: M3 — konsistent, krev presisering.
tau(DS-matrise) konvergerer mot Goldilocks: Q — opent spørsmål, testbar prediksjon.
