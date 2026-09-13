# Spectral Coherence as a Structural Metric — Paper 1 v1.1

Dato: 2026-06-25
Status: Revidert utkast v1.1

Tittel: "Spectral Coherence as a Structural Metric in Transformer Hidden States"
Undertittel: "Version 1.1 – Structural Classes, Architectural Limits, and Falsifiable Interpretation"

---

## Endringar frå v1.0

1. Empiriske krav tydeleggjort
2. Observasjonar skilt frå tolking
3. Kohærensklassar introdusert — ikkje faste representasjonar
4. Eksplisitte avgrensingar lagt til
5. Falsifiseringskriterium lagt til
6. Universell validering-språk fjerna
7. Goldilocks-grenser flytta til Appendix A som framtidig forskingsspørsmål

---

## Abstract

We introduce τ (tau), a dimensionless metric derived from the spectral entropy of
transformer hidden states, as an empirical measure of structural coherence. Version
1.1 separates empirical observations from theoretical interpretation. The experiments
support consistent ordering behaviour across evaluated conditions while showing that
absolute τ values remain architecture dependent. τ is therefore interpreted as a
structural diagnostic for coherence classes rather than a universal measure of
semantic identity.

---

## Seksjon 2: Theory

The central hypothesis is that transformer hidden states possess measurable structural
organization that can be quantified independently of semantic correctness.

### 2.1 Spectral Representation

For a hidden-state matrix H from a transformer layer, SVD produces singular values σ₁…σₙ.
Normalized energy distribution:

p_i = σ_i² / Σσ_j²

Spectral entropy:

S = −Σ p_i log(p_i)

### 2.2 Effective Rank

r_eff = exp(S)

### 2.3 Definisjon av τ

τ = exp(S) / n

der n er maksimal oppnåeleg rang (MERK: v1.1 brukar /n, tidlegare utkast brukte /sqrt(n)).

τ ≈ 0: høgt konsentrerte representasjonar
τ ≈ 1: nær uniform spektral distribusjon

### 2.4 Tolking (v1.1)

Empirisk: τ er ein reproduserbar strukturell statistikk.
Tolkingsmessig: arbeidshypotesen er at τ skil representasjonsklassar, ikkje faste semantiske tilstandar. Hypotesen er eksplisitt falsifiserbar.

---

## Seksjon 3: Structural Interpretation

The present experiments do not demonstrate convergence toward a single optimal
hidden-state representation. Instead, they suggest that hidden-state organization
occupies distinguishable regions of structural behaviour.

τ er tolka som å identifisere strukturelle kohærensklassar, ikkje faste representasjonspunkt.

Konseptuelt konsistent med:
- Ekvivalensklassar (matematikk)
- Universalitetsklassar (renormalisering)
- Attraktorbasseng (ikkje-lineær dynamikk)

Desse er hypotesar, ikkje empiriske konklusjonar.

---

## Seksjon 4: Experimental Design

Vekt på empirisk reproduserbarheit. Kvar τ-måling skal kunne reproduserast av andre med offentlege modell og standard SVD.

### 4.1 Modellar
Dekoder-berre og kodingsbaserte transformatorar, fleire parametersskalaer.

### 4.2 Datasett
Fem input-typar: naturleg språk, matematikk, kode, fleirspråkleg tekst, tilfeldig (kontroll).

### 4.3 Statistisk evaluering
τ-distribusjon, konfidensintervall, variansestimat, effektstorleik per eksperiment.

---

## Seksjon 5: Avgrensingar

- Evaluerer fire modellfamiliar (ikkje generell)
- Berre siste lag analysert
- τ måler strukturell organisasjon, ikkje semantisk korrektheit
- Arkitekturavhengige effektar er vesentlege
- Goldilocks-grenser er hypotetiske

---

## Seksjon 7: Discussion

Sentralt resultat (smalare enn v1.0): singular-verdi-spekteret til transformator-skjulte tilstandar inneheld målbar strukturell informasjon som varierer mellom inputklassar.

### 7.1 Fixed Points vs. Structural Classes (viktigaste omskrivinga)

Transformer-skjulte tilstandar bør ikkje forventast å konvergere til eit enkelt fikspunkt. Språkbehandling er kontekstuell, stiavhengig og arkitektur-sensitiv.

Ein strukturell klasse er svakare og meir realistisk enn eit fikspunkt. Tillèt lokal variasjon men bevarer målbart organisasjonsmønster.

τ bør ikkje lesast som at modellen har nådd ein spesifikk idealintern tilstand. Det bør lesast som evidens for at ulike inputregime kan indusere målbart ulike klasser av organisasjon.

### 7.2 Information Geometry

Spektral entropi er naturleg kopla til informasjonsgeometri via distribusjonsspread. Høg konsentrasjon = effektivt låg-dimensjonalt. Brei distribusjon = breiare effektiv subspace. Breiare er ikkje alltid betre — berre strukturelt annleis.

Neste steg: samanlikne τ med Fisher-informasjon, gjensidig informasjon mellom lag, aktiveringskovarians, intrinsisk dimensjonalitet, deltakelses-ratio.

### 7.3 Dynamical Systems

Dynamisk systemsspråk er fristande men må brukast forsiktig. Studien identifiserer ikkje attraktorar, invariante manifoldar eller Lyapunov-eksponentar. Berre spektral organisasjon ved valde punkt.

Framtidig: legg τ-trajektoriar over lag — kan koherent resonnering vise kontrollert ekspansjon/kompresjon, medan repetitiv generasjon kollapsar til låg-dimensjonal struktur?

### 7.4 Architecture Dependence (viktigaste negative funn)

Større parametertal garanterer ikkje høgare τ. Hindrar τ frå å vere ei enkel skaleringlov.

τ er følsam for arkitektur → nyttig fordi det avslører skilnader som parametertal åleine skjuler.

---

## Seksjon 8: Falsifiability

Tolkinga vert svekka eller avvist viss:
1. Brei replikering på tvers av modellfamiliar mislukkast
2. τ er dominert av tokenizer/padding/trunkerings-artefaktar
3. Modellar med radikalt ulik geometri produserer identiske τ-distribusjonar
4. Nedstrøms semantisk ytelse varierer uavhengig av τ

---

## Seksjon 9: Future Work

- Lagjewise analyse (alle lag, ikkje berre siste)
- Genereringstids-analyse (τ under autoregressiv dekoding)
- Oppgåvekorrelasjonsstudiar (τ vs. long-context reasoning, faktaoppkalling, matte, kode)
- Arkitekturkontrollerte studiar (matchet skala, tokenizer, treningsdata)
- Utforsking utanfor LLM (biologiske sekvensmodellar, GNN, RNN)

---

## Appendix A: Goldilocks Hypothesis

Tidlegare versjonar diskuterte eit Goldilocks-intervall [e^{-γ}, 1/ζ(3)] ≈ [0.5615, 0.8319].

I v1.1: Goldilocks-hypotesen er berre eit framtidig forskingsspørsmål. Noverande eksperiment validerer ikkje slike grenser for transformator-skjulte tilstandar. Eventuelle foreslåtte grenser krev validering på vesentleg breiare arkitekturar, datasett, lag og oppgåver.

---

## Epistemisk status (v1.1)

τ som reproduserbar strukturell diagnostikk: M4 (replikert over 4 modellar)
Rekkefølge koherent > tilfeldig > repetitivt: M3 (empirisk trend, ikkje universell lov)
Goldilocks-sona som grense: Q (framtidig forsking, ikkje validert)
τ som kohærensklasse-identifikator: M2 (strukturell hypotese, konsistent med data)

---

## Hovudforskjell frå v0.1 (theory/2026-06-21-paper1-spectral-coherence-draft.md)

| Aspekt | v0.1 | v1.1 |
|--------|------|------|
| Tau-formel | exp(H)/sqrt(n) | exp(S)/n |
| Tolking | Nærmar seg fikspunkt | Strukturelle klasser |
| Goldilocks | Hovudpåstand | Appendix — framtidig forsking |
| Arkitekturavhengighet | Bivirkning | Viktigaste negative funn |
| Universalitet | Implisert | Eksplisitt avvist |
| Falsifiseringskriterium | Lite | Fire eksplisitte kriterie |
