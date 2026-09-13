# CANONplus — Nullparameter-inferensmotor og Framleis-fikspunktstruktur

Dato: 2026-06-25
Kjelde: VectorPeak Research / Vallikat Peethamber — under-validert per due diligence 2026-06-22 (ingen peer review, ingen offentleg kode, ingen benchmark)
Status: M2 — strukturell analogi til Framleis; underliggjande VectorPeak-påstandar om null-parameter-kjerne ikkje offentleg verifiserte

---

## Hovudkonseptet

CANONplus er ein inferensmotor utan frie parametrar.

Tre eigenskapar definerer han:

1. **Sjølvdual matematisk objekt**: avleidd frå den einaste funksjonen som er perfekt sjølvspeila under transformasjon
2. **Null frie parametrar**: bandbreidde fastsett av sjølvdualitetsvilkåret (universell matematisk konstant)
3. **Karakteristisk kjerne**: kan skilje kva som helst to ulike sannsynsfordelingar frå kvarandre

Regularisering er eliminert via generalisert kryssvalidering (GCV).
Løysinga er eksakt og analytisk — ingen gradientnedstigning, ingen iterasjon.

CANONplus er Lag 2 i ein firelags-arkitektur.

---

## Sjølvdual funksjon = fikspunktvilkåret

Den sjølvduale funksjonen er den einaste funksjonen F kor:

F̂(ω) = F(ω)

der F̂ er den transformerte (t.d. Fourier-transformerte). Funksjonen er sin eigen transformerte.

I Framleis: fikspunktvilkåret er F(I*; sigma*) = I* — systemet er sin eigen referanse ved fikspunktet.

Sjølvdualitet er det same kravet i transformasjonsdomenet:
I* er stabil under F fordi F(I*) = I* (Framleis).
F̂ = F fordi transformasjonen gir det same objektet attende (sjølvdualitet).

Strukturell identitet: sjølvdualitet ER fikspunktvilkåret i transformasjonsdomenet.

---

## Null parametrar = I* er unikt bestemt (Banach)

Banach-fikspunktteoremet garanterer: om F er ein kontraksjon, finst det eksakt éin I*.
I* er ikkje valt — han emergerer frå F-strukturen.

CANONplus: bandbreidda er ikkje eit hyperparameter.
Han er fastsett av sjølvdualitetsvilkåret — den universelle matematiske konstanten som løyser F̂ = F.
Ingen brukarval. Ingen søkjealgoritme. Bandbreidda er tvungen av strukturen.

Mapping:
- Banach-garantert unik I* ↔ sjølvdualitetsvilkår gir unik bandbreidde
- alpha er ikkje valt, han emergerer frå F-strukturen ↔ bandbreidde er ikkje valt, ho emergerer frå kjerne-strukturen

---

## GCV eliminerer regularisering = sigma* les seg sjølv frå data

I Framleis: sigma* er referansepunktet systemet itererer mot.
Om sigma* er ukjend, må F estimere han frå tau_t.

CANONplus: GCV (Generalized Cross-Validation) eliminerer regulariseringsparameteren.
Regulariseringsparameteren er ein proxy for "kor sterkt held vi oss til data?"
GCV finn den optimale balansen direkte frå data — utan ekstern spesifikasjon.

GCV er F-operatoren som estimerer sigma* frå tau_t-observasjonar.

---

## Lukka-form-løysing = I* nådd i eitt steg

Standard optimering: gradientnedstigning, iterasjon, konvergens over mange steg.
Framleis: Banach-konvergens over mange F-iterasjonar.

CANONplus: lukka-form-løysing. Analytisk, eksakt, eitt steg.

Dette er det sterkaste Framleis-tilfellet: om I* kan nåast i eitt steg, er alpha = 1 — F(tau; sigma*) = sigma*.
Systemet kollapserer direkte til sigma* fordi det har perfekt kjennskap til referansen.

Sjølvdualitetsvilkåret gir det: den matematiske strukturen er så presis at sigma* = I* allereie er kjend analytisk.

---

## Karakteristisk kjerne = tau skil kohærensklassar

Karakteristisk kjerne: om K(x,y) er karakteristisk, kan ein skilje kva som helst to sannsynsfordelingar P ≠ Q ved å sjå på E_{P}[K(x,·)] ≠ E_{Q}[K(x,·)].

tau (exp(H)/n): eit mål som skil modellar med ulik strukturell kohærens.

Begge er skilje-metrikanar i sitt domene:
- Karakteristisk kjerne: skil sannsynsfordelingar (statistisk domene)
- tau: skil kohærensklassar (strukturelt domene)

Prediksjon: om tau-metrikken er berekna frå kjerne-representasjonane til CANONplus, vil tau-verdien for ulike datamengder vere eit mål for kor nær dei er same sigma*.

---

## Mapping til Framleis

| CANONplus | Framleis |
|-----------|----------|
| Sjølvdual funksjon (F̂ = F) | Fikspunktvilkår F(I*; sigma*) = I* |
| Sjølvdualitets-konstant | sigma* (universell referanse) |
| Null frie parametrar | I* unikt bestemt av F-strukturen (Banach) |
| Bandbreidde fastsett av struktur | alpha emergerer frå kontraksjonsfaktoren |
| GCV eliminerer regularisering | sigma* estimert direkte frå tau_t |
| Lukka-form-løysing (eitt steg) | F(tau; sigma*) = sigma* (alpha = 1, direkte konvergens) |
| Karakteristisk kjerne | tau som skilje-metrikk for kohærensklassar |
| Lag 2 i firelags-arkitektur | I* på nivå 2 av VΛLΦ-hierarkiet |
| Universal innleiing (alle datamodalitetar) | sigma* er modalitets-agnostisk referanse |

---

## Firelags-arkitektur og VΛLΦ

CANONplus er Lag 2 i ein firelags-arkitektur.

VΛLΦ: fire-lags-strukturen der:
- Lag 1: observasjonslag (tau_t)
- Lag 2: filtreringslag (F-operator → CANONplus)
- Lag 3: referanselag (sigma*)
- Lag 4: styringslag (EFA / AllowAction)

Om CANONplus er Lag 2, er han F-operatoren sjølv — den analytiske, nullparameter-kontraksjonen.

---

## Kopling til tidlegare Framleis-notat

Fraksjonal Schrödinger-notat (2026-06-25-kolesnikov-fnls-framleis.md):
Stasjonær tilstand ψ_s = I* er funksjonelt identisk med sjølvdualitets-fikspunktet til CANONplus.

Nevralt nett-notat (2026-06-25-nevralt-nett-framleis-identitet.md):
Batch normalization = tau-normalisering. CANONplus GCV = adaptiv batch-normalisering utan parameter.

Hjerne-aldring-notat (2026-06-25-hjerne-aldring-produkt-formel-framleis.md):
Søvn = F-iterasjon mot sigma*. CANONplus = F-operatoren som allereie veit sigma* (sjølvdualitet).

---

## Epistemisk status

MERK: Alle statuser nedanfor gjeld Framleis-mappingen som strukturell analogi. Dei reflekterer ikkje validering av dei underliggjande VectorPeak-påstandane, som manglar offentleg proof og kode.

Sjølvdual funksjon = fikspunktvilkår i transformasjonsdomenet: M2 — strukturelt analogt, ikkje formelt identisk; Gaussisk sjølvdualitet er matematisk reell men "universell konstant"-påstanden er upresis (normering, ikkje djup konstant).
Null-parameter = Banach-bestemt I*: M1 — same logiske rolle, men VectorPeak-påstanden er ikkje offentleg bevist; sigma-normalering er ikkje ein universalkonstant i same klasse som gamma eller zeta(3).
GCV = sigma*-estimering frå data: M2 — GCV er etablert statistisk teknikk (Golub/Heath/Wahba 1979); mappinga til Framleis er konsistent.
Lukka-form = alpha = 1: M1 — spekulativ tolking, ikkje bevist frå VectorPeak-sida.
Karakteristisk kjerne = tau-skilje: M2 — MMD-litteraturen (Gretton et al.) støttar Gaussisk kjerne som karakteristisk; mappinga til tau er ein hypotese.
