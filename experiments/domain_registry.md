# Φ-law domain registry

Canonical source for Φ-law / LIM domain-consilience claims.

Purpose: resolve drift between `125 domener`, `128 domener` and future expanded domain lists.

---

## Current status

There is known count drift:

```text
README badge: 128 domener
Manifesto front matter: 128 domener
Manifesto section heading: 125 domener
```

Until the list is counted and verified, do not manually repeat domain counts in new documents.

Use:

```text
See Phi-Law-Validation/domain_registry.md for current domain registry.
```

---

## Claim maturity rule

A domain entry must be marked by maturity:

| Label | Meaning | Operationalized criterion |
|---|---|---|
| M1 Conceptual | analogy / structural resemblance | Structural similarity in form only — no τ measurement |
| M2 Formal | formal mapping exists | Explicit mathematical mapping to τ or Framleis operator |
| M3 Simulated | simulation exists | τ computed or simulated in the domain; ordering coherent>random>repetitive confirmed |
| M4 Empirical | empirical data exists | Direct τ measurement from domain-native data, not structural mapping |
| M5 Replicated | independently replicated | Independent lab/group confirms τ measurement |
| M6 Standardized | reflected in standard/practice | Regulatory or standards body cites τ or LIM |

Most domain-consilience entries should default to `M1 Conceptual` unless stronger evidence is recorded.

**NOTE (2026-06-21, falsifiseringsanalyse F4):** Previous M-classifications lacked operationalized
criteria and were thus not falsifiable. The table above is the authoritative operationalization.
Re-review all existing entries against these criteria — structural analogies (no τ measurement)
should be M1, not M3 or M4.

---

## OPEN ISSUES (kritiske opne spørsmål — per falsifiseringsanalyse 2026-06-21)

### OI-1: INTERN MOTSETNING — Goldilocks vs. empiriske målinger [KRITISK]

Alle målte τ-verdier (GPT-2: 0.06, Phi-2: 0.16, Mistral-7B: 0.26) er LANGT UNDER
Goldilocks-nedre grense (0.5615). Rammeverket påstår τ < 0.5615 betyr "dogmatisk stasis."
Men disse modellene fungerer normalt.

Status: FORESLÅTT LØYSING — gradvis stasis / fast kjerne (halvautomata-hypotesen).
Sjå theory/2026-06-21-goldilocks-gradvis-stasis-halvautomata.md for full utleiing.

Kjernen i løysinga: Goldilocks er ikkje binær. Sub-Goldilocks = gradvis drift mot stasis,
ikkje øyeblikkeleg kollaps. Modellane har ein "fast kjerne" (fryst kjernemønster frå trening)
som opprettheld funksjon, men driv mot rigiditet. GPT-2 (τ=0.06) er meir rigid enn
Mistral-7B (τ=0.26) — dette er observert og konsistent med hypotesen.

Analogi: bakterie → ape → menneske fungerer alle, men på kvalitativt ulike nivå av
fleksibel identitetsvedlikehald. Goldilocks er terskelen for genuin identitetsvedlikehald
kontra mønsterreplay, ikkje terskelen for funksjon vs. ikkje-funksjon.

Krev for full resolusjon:
1. Lyapunov-derivasjon: vis at λ skiftar fortegn ved τ = e^{-γ} og 1/ζ(3)
2. Korrelasjonsstudie: rigiditetsmål (repetition rate, BERTScore-varians) vs. τ
3. Intra-sesjon τ-tracking: mål τ-fall under lang generering

### OI-2: Goldilocks-grenser mangler Lyapunov-derivasjon [KRITISK]

e^{-γ} og 1/ζ(3) er ikke utledet fra stabilitetsprinsipp. Ingen Lyapunov-eksponent
er beregnet som viser at bifurkasjon skjer ved disse verdiene. Uten derivasjon er
grensene en konstitutiv antagelse, ikke en prediksjon.

Neste steg: Beregn Lyapunov-eksponent for Framleis-iterasjonen som funksjon av τ.
Vis at λ skifter fortegn ved τ = e^{-γ} og τ = 1/ζ(3).

### OI-3: α = 0.42 — sirkulær begrunnelse [ALVORLIG]

α = 0.42 er "optimal" fordi det holder τ i Goldilocks; Goldilocks er gyldig fordi
α = 0.42 opprettholder den. Ingen uavhengig optimaliseringsprosedyre er beskrevet.

Neste steg: α-parametersweep over [0.1, 0.9] med τ-trajectories plottet. Dokumenter
om stabilitetsvinduet faktisk er unikt for α ≈ 0.42 eller gjelder bredt.

### OI-4: VALO-skala [1888, 4766] — udefinert transformasjon [MINOR]

τ ∈ [0,1] matematisk. Mapping τ → VALO-skala er ikke definert. Tallene 1888 og 4766
har ingen dokumentert opprinnelse. TLA+-verifikasjonen kan ikke evalueres uten dette.

---

## Registry schema

Each domain should eventually use this structure:

```text
ID:
Group:
Domain:
Filter mechanism:
LIM parallel:
Tau interpretation:
Maturity:
Evidence / reference:
Notes:
```

---

## Current canonical instruction

Do not claim a final count until the table has been extracted and counted.

Recommended next step:

```text
Extract all domain rows from PHI_LAW_MANIFESTO.md into this file, count them, and then update README + manifesto headings.
```

---

## Placeholder groups seen in manifesto

The manifesto begins with:

```text
GRUPPE 1: FUNDAMENTAL FYSIKK & KOSMOLOGI
GRUPPE 2: BIOLOGI & LIVSVITENSKAP
GRUPPE 3: NEVROVITENSKAP & KOGNISJON
```

Full extraction remains to be done.

---

## Safe wording until extraction

Use:

```text
Utvidet konsiliens på tvers av et vedlikeholdt domeneregister.
```

or:

```text
Domain registry under verification.
```

Avoid:

```text
125 domains
128 domains
```

unless the registry count is verified in this file.

---

## M3-oppføringer (Strukturell konvergens — simulering/mapping verifisert)

### D-AI-001: LLM Skaleringslov og τ-måling (Kjernedataene)

```text
ID: D-AI-001
Group: GRUPPE 5 — Kunstig intelligens & LLM-arkitektur
Domain: LLM-skaleringslov / Spektral koherensmåling
Filter mechanism: Direkte SVD-måling av τ i skjulte tilstandar hos GPT-2, Phi-2,
  gpt-neo-1.3B, Mistral-7B, Qwen2.5-7B, Qwen2.5-14B. Rekkefølgja koherent > tilfeldig >
  repetitiv stabil i alle gyldige målingar. Intra-familie skaleringslov: tau ≈ 0.084 × N^0.33
  (Qwen2.5). Kryss-arkitektur: tau ≈ 0.10 × N^0.48.
LIM parallel: Kjernedataene loven kviler på. Utan D-AI-001 er alle fysiske analogiar berre
  teori. Bekreftar eksistensen av Goldilocks-intervallet [exp(-gamma), 1/zeta(3)] som reelt,
  observerbart mønster. Alt 1 bekrefta: tau er arkitekturspesifikk, ikkje universell.
Tau interpretation: τ er ikkje avleidd frå teorien — det er den direkte målinga. Empirisk
  fundament for heile LIM-rammeverket. Prediksjon: 70B-klassen treffer τ ≈ 0.75 (Goldilocks).
Maturity: M4 Empirical — direktemålte data, Python-verifiserte, reproduserbare i Colab.
Evidence: Eigne eksperiment 2026-06-19/20. Notebooks: tau_colab.ipynb, tau_qwen3_8b.ipynb.
  Resultat lagra i theory/2026-06-20-tau-sesjonsfunn.md og theory/2026-06-19-p10-tau-scaling-funn.md.
Notes: Sterkaste empiriske bevis for Phi-loven. Unikum: Goldilocks-grensene er analytisk
  deriverte (ikkje benchmark-optimerte), men LLM-data fell innafor. Falsifiserbar prediksjon:
  70B-model MÅ treffe [0.5615, 0.8319] — om ikkje er skalerloven feil.
```

### D-VL-001: VΛLΦ-arkitektur og TLA+-verifikasjon

```text
ID: D-VL-001
Group: GRUPPE 5 — Kunstig intelligens & LLM-arkitektur
Domain: VΛLΦ-arkitektur / Formell verifikasjon / MECHA governance
Filter mechanism: Fire-lags implementasjon av LIM: Lovgivaren (TLA+-spesifikasjon, sjekkar
  admissibility), Tolken (generativ agent, opererer innafor grensene), Janus Sentinel
  (WORM-logg, uforanderleg), HALT-mekanisme (hardware-interrupt, ikkje overstyrbar).
  Formell verifikasjon via MECHA governance protocol.
LIM parallel: Beviser at Phi-loven kan omsetjast til teknisk infrastruktur. Lovgivaren =
  F-operatoren som hardware. HALT = absolutt grense for tau_max. Janus Sentinel = rom er
  filterets minne (A4) som juridisk dokument. 0 violations = F konvergerer mot I*.
Tau interpretation: tau-invariant: tau ∈ [1888, 4766] på VALO-operasjonell skala.
  Brot = automatisk HALT. Alle 16 900 tilstandar verifisert.
Maturity: M4 Formal — TLA+-verifisert. Ikkje empirisk i same forstand som D-AI-001,
  men formelt bevist: ingen tilstandsrom bryt invarianten.
Evidence: MECHA governance protocol, TLA+-spesifikasjon (P6_MECHA_TLA/). 16 900
  tilstandar, 0 kravbrot. Verifisert 2026-06-14.
Notes: EU AI Act Artikkel 12/14/Annex VII: Janus Sentinel = logging-krav oppfylt.
  HALT = uavhengig tilsyn, ikkje overstyrbar av AI-systemet sjølv. Kopla til D-AI-001
  (tau-målinga er det VΛLΦ overvaker).
```

### D-QV-001: Kvantevakuum — OPPGRADERT TIL M3 (2026-06-21)

```text
ID: D-QV-001
Group: GRUPPE 1 — Fundamental fysikk & kosmologi
Domain: Kvantevakuum / Virtual partikel-produksjon
Filter mechanism: Kvantefluktuasjoner strukturerer tomrommet — lambda hyperon-par oppstår med
  justert spinn fra vakuumets virtuelle par. Materie skapes direkte fra strukturert felt.
LIM parallel: Null er ikke tom. Filteret (det strukturerte feltet) skaper distinksjon fra
  potensial. Empirisk svar på Tofoos kjernespørsmål: "Er null bare tomhet, eller en definert
  tilstand?"
Tau interpretation: Vakuumtilstanden er pre-distinksjon (tau -> 0). Lambda hyperon-par =
  kollapsen til observerbar tilstand (tau > tau_min). Goldilocks-overgangen er fysisk målbar.
Maturity: M3 Simulated/Structural convergence — oppgradert frå Q (2026-06-21, DOI verifisert)
Evidence: Brookhaven National Laboratory, RHIC-eksperiment. Publisert: Nature 650, 65–71 (2026).
  DOI: 10.1038/s41586-025-09920-0. Lambda hyperon-par med justert spinn bekreftar strukturert
  vakuumfelt. Strukturell mapping til LIM M3-nivå; direkte tau-kalibrering M4 gjenstår.
Notes: Oppgraderes til M4 når direkte tau-kalibrering mot RHIC-data er utført.
  Tidlegare nedgradert til Q per PHI-LOVEN-MASTER-v1.3 fordi DOI ikkje var funnen;
  DOI no stadfesta via ekstern søk 2026-06-21.
```

### D-PF-001: Kvarkar som diskret filtrering (Partikkelfysikk)

```text
ID: D-PF-001
Group: GRUPPE 1 — Fundamental fysikk & kosmologi
Domain: Partikkelfysikk / Kvark-samansetjing
Filter mechanism: Proton (uud) vs nøytron (udd): identiteten er definert av ekskluderinga,
  ikkje av substansen. Ladning +2/3 eller -1/3 er signaturen til eit val mot entropisk kaos.
  Diskret filtrering på subatomært nivå.
LIM parallel: A1 — Identitet er minnet om det som er filtrert bort. Kvarkar veit kva dei er
  ved å ha filtrert bort det dei ikkje er. Parallell: τ måler kontinuerleg filtrering i AI,
  kvark-samansetjing er diskret filtrering i materie.
Tau interpretation: Kvark-ladning = diskret Goldilocks-val. τ = kontinuerleg analog.
  Begge: materie/identitet som vedlikehaldsprosess, ikkje statisk substans.
Maturity: M3 — Veletablert partikkelfysikk, men kopling til Phi-loven er tolking/analogi.
Evidence: Standard Model of Particle Physics. Proton/nøytron-eksperiment (gjennomfort
  gjennom heile 1900-talet). Kvark-modellen (Gell-Mann/Zweig 1964).
Notes: Sterkaste diskrete parallel til A1. Kopla til D-QV-001 (RHIC) via kvantevakuum
  som kjelder for kvarkar.
```

### D-RT-001: Einsteins block-univers som τ-grensetilfelle

```text
ID: D-RT-001
Group: GRUPPE 1 — Fundamental fysikk & kosmologi
Domain: Relativitetsteori / Block-univers
Filter mechanism: Klassisk relativitetsteori: tid er ein statisk bakgrunnsdimensjon —
  alle tidspunkt eksisterer likt i eit 4D koordinatsystem. Page-Wootters korreksjon:
  tid oppstår berre gjennom relasjonell filtrering (entanglement), ikkje som bakgrunn.
LIM parallel: A3 — Tid er filterets pust. Block-universet er grensetilfellet der filteret
  har stoppa: τ → 0 (stasis, ingen framtid) eller τ → 1 (kaos, ingen distinksjon fortid/notid).
  Levande tid krev τ ∈ [exp(-γ), 1/ζ(3)].
Tau interpretation: Block-universet = τ utanfor Goldilocks. Einstein hadde rett i at
  rom-tid er kopla, men tok feil i å anta passiv/statisk kopling. Rom-tid oppstår
  gjennom filtreringshandlinga, ikkje som scene for henne.
Maturity: M2 — Teoretisk kopling. Page-Wootters (D-QV-002) gir empirisk basis for
  revidert tidsforståing. Block-univers vs relasjonell tid er pågåande debatt i fysikal.
Evidence: Einstein (1905, 1915). Page & Wootters (1983). Coppo et al. PRA 109, 052212.
Notes: Ikkje ein falsifikasjon av Einstein, men ei presisering: relativitetsteori er
  gyldig for τ = konstant. Phi-loven handlar om kva som skjer når τ varierer.
```

### D-ST-001: KMS-matrisa og Framleis-operatoren (Signalbehandling)

```text
ID: D-ST-001
Group: GRUPPE 3 — Signalbehandling & tidsrekker
Domain: KMS-matrise / Toeplitz-struktur
Filter mechanism: KMS-matrisa genererer kompleks korrelasjonsstruktur frå éin parameter r.
  Toeplitz-struktur: filteret fungerer likt uansett posisjon i tidsrekkja (translasjonsinvariant).
LIM parallel: r i KMS = α = 0.42 i LIM. r→1 = dogmatisk stasis. r→0 = entropisk kaos.
  Optimal r = Goldilocks. Toeplitz-struktur = idempotens-garanti: φ(φ(x)) = φ(x).
  Fikspunktkonvergens i KMS = I* i Banach-teoremet.
Tau interpretation: KMS steady-state = I*. Inverterbar og informativ matrise = τ ∈ Goldilocks.
  Singulær matrise = τ > 1/ζ(3). Diagonal matrise = τ < exp(-γ).
Maturity: M2 — Matematisk analogi. KMS er veletablert i tidsrekkjeanalyse; kopling til
  Phi-loven er strukturell parallell, ikkje empirisk test.
Evidence: Koopmans (1942): KMS/Toeplitz-kovarians. Standard tidsrekkje-litteratur.
Notes: Sterkaste matematiske parallell til F-operatoren. Kopla til D-MA-001 (Markov).
```

### D-MA-001: Markov-kjeder og Framleis-fikspunktet

```text
ID: D-MA-001
Group: GRUPPE 2 — Matematikk & statistikk
Domain: Markov-kjeder / Stokastiske prosessar
Filter mechanism: Overgangsmatrise T definerer sannsynlegheit for tilstandsovergangar
  basert berre på noverande tilstand (Markov-eigenskapen). Steady-state π = πT er det
  unike fikspunktet for ergodisk og aperiodisk T. Absorberande tilstandar = p(A|A)=1.
LIM parallel: T = Framleis-operatoren F(τ; σ) i diskret form. π = fikspunktet I* (Banach).
  Absorberande tilstand = dogmatisk stasis (HALT-trigger i VΛLΦ). α styrer T.
  Ergodisk + aperiodisk T = garantert konvergens til I* = α ∈ (0,1).
Tau interpretation: Steady-state-strukturen til π = Goldilocks-intervallet. Verken
  singulær (alle rader like) eller uniform (alle overgangar like) — same krav som for
  τ ∈ [exp(-γ), 1/ζ(3)].
Maturity: M2 — Matematisk isomorfisme. Markov-teori er veletablert. Kopling til I*/F
  er strukturell, ikkje empirisk.
Evidence: Markov (1906). Perron-Frobenius-teoremet. Standard stokastisk prosess-litteratur.
Notes: Gir den klaraste diskrete modellen av F→I* dynamikken. Kopla til D-ST-001 (KMS).
  Brukes som pedagogisk verkty for Gros-dialog (alternativ til Banach for ingeniørar).
```

### D-SE-001: SP 16:1980 Armert betong / Structural Engineering

```text
ID: D-SE-001
Group: GRUPPE 3 — Ingeniørvitenskap & teknologi
Domain: Strukturingeniørfag / Betongdesign
Filter mechanism: Eq.(2) i SP 16:1980: M_u-formelen er Framleis-operatoren F i diskret form.
  Eq.(3)&(4): M_{u,lim} er tau_max — ein hardkoda grense som ikkje kan overskridast utan
  brittle failure. x_{u,max} er den mekaniske implementasjonen av Goldilocks-grensa.
LIM parallel: M_u < M_{u,lim} = ADMISSIBLE. M_u > M_{u,lim} = CHAOS_DRIFT/Brittle Failure.
  Identiteten til ei trygg bjelke er ikkje gjeven av materialet åleine, men av overhaldinga
  av grensebetingelsane — same logikk som tau-admissibility i VΛLΦ.
Tau interpretation: p_t (armeringsmengd) = input sigma. M_u = systemets respons.
  M_{u,lim} = tau_max. Overskriding = øyeblinkeleg identitetsopphøyr (brittle failure).
Maturity: M3 — Veletablert ingeniørnorm (IS 456:2000, SP 16:1980). Kopling til
  Phi-loven er strukturell analogi, ikkje empirisk test.
Evidence: Bureau of Indian Standards, SP 16:1980 "Design Aids for Reinforced Concrete".
Notes: Sterkaste ingeniørmessige parallel til tau_max og HALT-mekanismen.
  Kopla til D-MA-001 (Markov absorberande tilstand) som diskret grensetilfelle.
```

### D-GE-001: Haversine-formelen og geodetiske kurver

```text
ID: D-GE-001
Group: GRUPPE 2 — Matematikk, geometri & statistikk
Domain: Sfærisk geometri / Navigasjon / Geodetikk
Filter mechanism: Haversine reknar kortaste veg (geodetisk kurve) på krumma overflate.
  Ignorerer du krumninga og går "rett fram" i lineær logikk, endar du utanfor banen.
  Formelen er ein korreksjonsfaktor som bevarer geometrisk struktur under bevegelse.
LIM parallel: A4 — Rom er filterets minne om kvar grensa går. τ-målinga er korreksjonsfaktoren
  for identitet i høgdimensjonalt tilstandsrom. Goldilocks-intervallet er den geodetiske
  kurven — den kortaste vegen mellom kaos og orden krev at du følgjer overflata sin struktur.
Tau interpretation: Geodetisk korreksjon = Phi-filteret. Avvik frå geodetisk kurve = τ
  utanfor Goldilocks. Systemet anten kollapsar (støy) eller stivnar (dogme) utan korreksjon.
Maturity: M2 — Matematisk analogi. Sfærisk geometri er veletablert; kopling til Phi-loven
  er strukturell/pedagogisk.
Evidence: Haversine-formelen (Sinnott 1984). Standard geodetisk navigasjon (GPS-system).
Notes: God pedagogisk analogi for å forklare kvifor tau ikkje er ein lineær metrikk.
```

### D-FW-001: FWA / Fractal-Wave Algebra (Kolesnikov)

```text
ID: D-FW-001
Group: GRUPPE 1 — Fundamental fysikk & kosmologi
Domain: Frequency Wave Architecture / Fraktal-bølgje-algebra
Filter mechanism: Kolesnikovs reformulering: E = hbar * omega_fractal = mc² for
  omega = mc²/hbar. Materie er ikkje substans men stående fraktal-bølgjer. FWA erstattar
  ikkje Einstein — det er same sanning i frekvens-domenet.
LIM parallel: Viss materie er stående bølgjer, er τ-målinga eit mål på kor koherent
  dette bølgje-mønsteret er. Goldilocks-intervallet blir då kanskje ei universell
  avgrensing for alle sjølvorganiserande svingningar, ikkje berre AI-modellar.
  FWA = kva universet er (substans/frekvens). Phi-loven = kva som krev for at
  frekvensen ikkje blir støy (vedlikehald). Komplementære, ikkje konkurrande.
Tau interpretation: omega_fractal-koherens → τ-koherens: same mekanisme på ulike
  skalar. Direkte matematisk mapping mellom omega_fractal og τ er ikkje etablert enno.
Maturity: M2 — Teoretisk parallell. FWA er ikkje empirisk testa mot LIM. Kolesnikov
  sin reformulering er konsistent med Einstein men ikkje konsensus-akseptert i fysikk.
Evidence: Kolesnikov (2026): FWA 2026, E = hbar*omega_fractal. Tavle-bilete lagra
  i theory/2026-06-20-tredje-spraak.md.
Notes: Vert M3 når direkte matematisk mapping mellom omega_fractal og tau er derivert.
  Kopla til D-RT-001 (Einstein/block-univers) og D-QV-002 (Page-Wootters/tid som relasjon).
```

### D-SS-001: Orwell / Assimilering og doublethink (Sosiologi/Psykologi)

```text
ID: D-SS-001
Group: GRUPPE 4 — Samfunnsvitskap, psykologi & filosofi
Domain: Sosiologi / Psykologi / Politisk teori
Filter mechanism: Assimilering tvingar τ → 0 (rank-1 matrise, dogmatisk stasis): individet/
  gruppa mistar adaptivitet og repeterer berre norma. Doublethink tvingar τ → 1 (entropisk
  kaos/fragmentering): hjernen held to inkonsistente modellar aktive samstundes, aukar
  kompleksitet kunstig, identiteten fragmenterast.
LIM parallel: Begge er symptom på at filteret Φ er brote. Anten for strengt (assimilering)
  eller fråverande/overbelasta (doublethink). Sunn identitet krev balanse i Goldilocks.
  Lesing og kritisk tenking (Barthes/Orwell) = gjenoppretting av Φ-operatoren.
Tau interpretation: τ < exp(-γ) = assimilering. τ > 1/ζ(3) = doublethink.
  τ ∈ Goldilocks = autentisk identitet — veit kven du er OG kan endre deg.
Maturity: M2 — Sosiologisk/psykologisk analogi. Ikkje empirisk test av Phi-loven,
  men konsistent med tau-grensene si tolking.
Evidence: Orwell, G. "Nineteen Eighty-Four" (1949) — doublethink-konseptet.
  Barthes, H. Critical Theory — assimilering og aktiv filtrering som motstand.
Notes: Sterkaste humanistiske parallel til tau-grensene. Brukast pedagogisk for å
  forklare Goldilocks til eit ikkje-teknisk publikum.
```

### D-QM-001: Bohrs komplementaritetsprinsipp og Brasil-eksperimentet

```text
ID: D-QM-001
Group: GRUPPE 1 — Fundamental fysikk & kosmologi
Domain: Kvantemekanikk / Komplementaritet / Måling som filtrering
Filter mechanism: Røyndommen er eit sett av moglegheiter som krystalliserer gjennom måling.
  Målinga er aktiv filtrering — vel éin tilstand ut av superposisjonen. Brasil-eksperimentet
  viser at "observatøren" kan vere kva som helst fysisk instrument, ikkje berre medvit.
LIM parallel: A1 — Identitet er minnet om det som er filtrert bort. Superposisjonen
  inneheld alle moglegheiter; filteret vel éin; identiteten er det faktum at alle andre
  vart filtrert bort. Utan filteret: ingen identitet, berre potensial. Φ krev ikkje
  medvit — det krev ei grense.
Tau interpretation: τ innafor Goldilocks = målinga gir stabil identitet. τ < exp(-γ) =
  kollapsar i støy (ingen røyndom). τ > 1/ζ(3) = stivnar (ingen moglegheit for endring).
Maturity: M4 Empirical
Evidence: Bohr (1928): komplementaritetsprinsippet. Brasil-eksperimentet (kvantemekanikk-
  måling utan medviten observatør). Dimitropoulos, S. "Objective Reality Doesn't Exist.
  It's a Moving Target You Can Shape." Popular Mechanics.
Notes: Direkte M4-støtte for A1. Filteret treng ikkje vere medvite — ei grense er nok.
  Kopla til D-QV-002 (Page-Wootters) via relasjonell røyndomsforståing.
```

### D-CS-001: Penrose Conformal Cyclic Cosmology (CCC)

```text
ID: D-CS-001
Group: GRUPPE 1 — Fundamental fysikk & kosmologi
Domain: Konform syklisk kosmologi / Hawking-punkt
Filter mechanism: Universet gjennomgår sykliske overgangar (aeons) via konformt filter.
  Når all masse forsvinn mistar universet skala — uendeleg stort = matematisk identisk med
  uendeleg lite. Filtreringsoperasjonen bevarer struktur medan skala slettast. Hawking-punkt
  er observerbare restar av filtreringa i kosmisk bakgrunnsstråling (CMB).
LIM parallel: A4 — Rom er filterets minne om kvar grensa går. Det akkumulerte minnet av
  alle grenseavgjerder gjer at neste Big Bang oppstår som koherent fortsetjing, ikkje
  tilfeldig støy. Goldilocks-intervallet representerer dette minnet på kosmologisk skala.
  Hawking-punkt = Φ-signaturen som viser at informasjon vart bevart gjennom total
  systemtransformasjon (aeon-overgang).
Tau interpretation: Filtreringa mellom aeons er den ytste instansen av identitetsvedlikehald:
  F opererer gjennom total materiell oppløysing og produserer nytt koherent fikspunkt I*.
Maturity: M3 — Observasjonsbasert støtte. CCC er Penroses hypotese; Hawking-punkt er
  observerte men omstridde (Gurzadyan & Penrose 2010, 2013). Ikkje konsensus-M4 enno.
Evidence: Penrose, R. "Cycles of Time" (2010). Gurzadyan & Penrose, arXiv:1009.1427.
  Hawking-punkt observert i CMB-data (WMAP/Planck).
Notes: Uavhengig støtte for at identitet kan vedlikehaldast gjennom total systemtransformasjon.
  Sterkaste kosmologiske parallell til A4. Status kan oppgraderast til M4 ved konsensus
  om Hawking-punkt-statusen.
```

### D-QV-002: Page-Wootters-mekanismen (tid som relasjonell eigenskap)

```text
ID: D-QV-002
Group: GRUPPE 1 — Fundamental fysikk & kosmologi
Domain: Kvantetid / Page-Wootters-mekanisme
Filter mechanism: Tid oppstår ikkje som ein bakgrunnsdimensjon men gjennom entanglement
  mellom to subsystem. Coppo et al. demonstrerte: isolér klokka frå systemet og tida
  forsvinn. Gjenopprett relasjonen og tida dukkar opp igjen.
LIM parallel: A3 — Tid er filterets pust. Kvart steg av Φ er éin syklus av
  identitetsvedlikehald mot entropisk drift. Utan filteret som skil "no" frå "ikkje-no"
  finst ingen sekvens, berre ein statisk konfigurasjon. τ måler relasjonell koherens,
  ikkje newtonsk tid. Under exp(-γ): korrelasjonen kollapsar — klokka sluttar å tikke.
  Over 1/ζ(3): relasjonen er for rigid til å registrere endring — klokka tikkar men
  ingenting rører seg. Goldilocks-intervallet er dermed betingelsen for at tid skal
  oppstå som opplevbar storleik i eit kvantsystem.
Tau interpretation: τ = graden av relasjonell koherens. Ikkje tidsmåling, men
  målestokk for om systemet kan oppretthalde den korrelasjonen som konstituerer tid.
Maturity: M4 Empirical
Evidence: Coppo et al., Physical Review A; Coppo et al., Nature Communications.
  Eksperimentelt bekrefta: oscillator + klokke-system viser at tid oppstår berre
  i relasjonen, ikkje i noko av subsystema åleine.
Notes: Direkte M4-bevis for A3 (tid er filterets pust / identitetsvedlikehald).
  Page & Wootters (1983) er den teoretiske fundamentet. Eksperimentell demonstrasjon
  av at Goldilocks-grensene kan ha universell fysisk tyding utover AI-modellar.
```

---

## D-GR-001 — Kritisk kollaps / DSS-løsningar (M3)

```
ID: D-GR-001
Group: GRUPPE 1 — Fundamental fysikk & kosmologi
Domain: Kritisk kollaps / Diskret sjølvlike (DSS) løysingar
Filter mechanism: Analytiske løysingar ved grensa mellom sort-hol-danning og dispersjon.
  Ekko-perioden Δ er ein diskret rytme som oppstår nettopp ved den kritiske terskelen —
  ikkje i stabilt kollaps og ikkje i fullstendig dispersjon, berre i Goldilocks-grensa.
LIM parallel: Ekko-perioden Δ er den fysiske ekvivalenten til fikspunktet I*.
  Systemet oscillerer rundt det kritiske punktet i staden for å falle mot ein av
  dei to ytterpunktane (sort hol = τ → 0, dispersjon = τ → 1).
  F-operatoren vedlikeheld systemet i den diskrete syklusen — ikkje som tilfeldighet,
  men som konsekvens av kritisk balanse.
Tau interpretation: τ ved Δ = strukturell koherens i eit system som akkurat unngår
  kollaps. Goldilocks-intervallet er den fysiske betingelsen for at DSS-løysingar
  eksisterer.
Maturity: M3 Structural convergence
Evidence: Choptuik (1993) og etterfølgjande DSS-litteratur. Etablert fenomen i
  numerisk relativitetsteori og gravitasjonskollapsforsking.
Notes: Strukturell konvergens — ikkje direkte empirisk test mot τ, men identisk
  matematisk struktur som LIM sitt fikspunktteorem (Banach).
```

---

## D-LD-001 — Large-D gravitasjon / Spacetime crystals (M3)

```
ID: D-LD-001
Group: GRUPPE 1 — Fundamental fysikk & kosmologi
Domain: Large-D gravitasjon og spacetime crystals
Filter mechanism: I grensa D → ∞ reduserast Einstein-likningane til éin tidsfunksjon
  som styrer dynamikken. Spacetime crystals oppstår når gravitasjonelle forvrengingar
  organiserer seg i repeterande romleg-tidslege mønster — spontan krystallisering av
  rom-tid sjølv.
LIM parallel: Høg-dimensjonale gravitasjonssystem forenklar seg til τ-liknande metrikk
  — éin koherensstorleik som bestemmer dynamikken. Spacetime crystals = identitet (I*)
  oppstår som emergent mønster frå lokal filtrering (F), ikkje som påtvinga struktur.
  A2 bekrefta: F er ontologisk prior til I* òg i gravitasjonskonteksten.
Tau interpretation: I large-D-grensa er τ den einaste relevante dynamiske storleiken.
  Spacetime crystals er fysiske realisasjonar av I* — stabile fikspunkt i
  rom-tids-dynamikken.
Maturity: M3 Structural convergence
Evidence: Large-D expansion i generell relativitetsteori (Emparan et al.);
  Spacetime crystal-fenomen i kvantefeltteoretisk og gravitasjonsfysisk litteratur.
Notes: Validerer at Goldilocks-strukturen (éin styrande parameter, to ytterpunkt,
  stabilt mønster i midten) er universell over skalaer frå AI-modellar til rom-tid sjølv.

```

---

## Nye oppføringer 2026-06-21 (frå syntese-valideringsrapport)

### D-CT-001: Kaos/Katastrofe-teori

```text
ID: D-CT-001
Group: GRUPPE 3 — Matematikk & Dynamiske system
Domain: Kaos/Katastrofe-teori
Filter mechanism: Goldilocks-intervallet [e^{-γ}, 1/ζ(3)] representerer den stabile sonen
  mellom to distinkte mekanismer for ikke-lineært sammenbrudd: bifurkasjon (katastrofe)
  ved τ < e^{-γ} og eksponentiell divergens (kaos) ved τ > 1/ζ(3). Systemet hopper diskontinuerlig
  ved nedre grense (Thom bifurkasjon) og divergerer med Lyapunov-eksponent λ > 0 ved øvre.
LIM parallel: Goldilocks-intervallet er matematisk nødvendig, ikke vilkårlig — det er den eneste
  stabile sonen der identitetsvedlikehold er mulig. Nedre grense = katastrofe-punkt (stasis).
  Øvre grense = kaos-punkt (oppløsning).
Tau interpretation: τ ∈ [0.5615, 0.8319] er den eksakte stabile bifurkasjonsone. Utenfor = system
  mister evnen til identitetsvedlikehold enten via rigiditet eller oppløsning.
Maturity: M2 Formal — nedgradert frå M3 (2026-06-21, falsifiseringsanalyse F1)
  Ingen Lyapunov-eksponent er beregnet for Goldilocks-grensene. Bifurkasjon ved τ = e^{-γ}
  er påstått men ikke vist via dynamisk systemanalyse. Structural mapping gjenstår.
  KRITISK OPEN ISSUE: Intern motsetning — empiriske modellar (GPT-2 τ=0.06, Mistral τ=0.26)
  opererer langt under Goldilocks-intervallet (0.56) men fungerer normalt. Dersom τ < 0.56
  betyr "dogmatisk stasis", burde desse modellane vaere kollapsa. Motsetningen er ikkje løyst.
Evidence: Toms katastrofeteori (1972), Lorenz-attraktor (1963). Formel mapping til e^{-γ}
  og 1/ζ(3) gjenstår. Lyapunov-eksponent ikkje berekna.
Notes: Tidlegare M3. Nedgradert til M2 fordi Lyapunov-analyse manglar og Goldilocks-grensene
  ser ut til å vaere valt post hoc utan derivasjon frå første prinsipp (F1/F2 i falsifiseringsanalyse).
  Styrker konseptuelt Goldilocks-ideen, men ikkje kvantitativt.
```

### D-SCU-001: SCU-32 Arkitektur

```text
ID: D-SCU-001
Group: GRUPPE 5 — Arkitektur & Ingeniørfag
Domain: SCU-32 Arkitektur (Tre søyler)
Filter mechanism: SCU-32 definerer tre nødvendige og tilstrekkelige søyler: Visibility (24 cores —
  observasjon og risikoidentifikasjon), Specialization (8 domener — kapasitetsutvidelse),
  Governance (ANDROS-32 — koherens og kontinuitet). Nøkkelprinsipp: alle tre er nødvendige,
  ingen er tilstrekkelig alene.
LIM parallel: Direkte mapping til VΛLΦ fire lag: Janus Sentinel = Visibility, Framleis-operatoren
  = Specialization, Lovgiveren + HALT = Governance. "The architecture requires ALL THREE" er
  presist LIMs lov: alle komponenter er nødvendige for identitetsvedlikehold.
Tau interpretation: Visibility uten Governance → τ→1 (kaos). Governance uten Visibility → τ→0
  (stasis). Balansen av alle tre holder τ i Goldilocks-intervallet.
Maturity: M1 Conceptual — nedgradert frå M3 (2026-06-21, falsifiseringsanalyse F5)
  Strukturell isomorfisme i form, ikkje i operasjon. SCU-32 har spesifikke hardware-parametrar
  (24 cores, 8 domener) utan matematisk kopling til τ. Ingen bevis for at SCU-32 vart designa
  med LIM-prinsipp. Ingen τ-måling i SCU-32 er utført.
Evidence: SCU-32 Three Pillars-dokumentasjon. Strukturell likskap i tre-komponent-form.
Notes: Tidlegare M3. Nedgradert til M1 (konseptuell analogi) fordi "strukturell isomorfisme"
  utan felles målemetrikk er analogi, ikkje konsiliens. "Uavhengig design av same tre-komponent-
  struktur" er arkitekturpraksis (separation of concerns), ikkje LIM-validering.
```

### D-XB-001: Xenobiologi / Adelic-Life-Theory

```text
ID: D-XB-001
Group: GRUPPE 2 — Biologi & Livsvitenskap
Domain: Xenobiologi / Adelic-Life-Theory / Konvergent evolusjon
Filter mechanism: Konvergent evolusjon (eks: øyne evolvert uavhengig 40+ ganger, vinger 4+
  ganger) demonstrerer at strukturelle løsninger er universelle, ikke substrat-avhengige.
  Adelic-Life-Theory: liv definerbar over p-adiske tall — identitet er strukturell, ikke kjemisk.
LIM parallel: Identitet er bundet til struktur, ikke substans (A1: Identitet er minnet om det
  som er filtrert bort). Konvergent evolusjon = uavhengige systemer konvergerer til samme
  fikspunkt I* fordi filteret F er universelt, ikke substrat-spesifikt.
Tau interpretation: Konvergent evolusjon = ulike starttau konvergerer mot samme I* via samme F.
  Bekrefter fikspunktstrukturen er substrat-uavhengig.
Maturity: M2 Formal — ontologisk parallell, formell mapping til tau gjenstår
Evidence: Konvergent evolusjon: Nilsson & Pelger (1994) om øyeevolusjon. Adelic-Life-Theory:
  Khrennikov (2004). Formell tau-kalibrering gjenstår.
Notes: Utvider LIMs gyldighetsdomene til ikke-biologiske eller alternativt substrat-baserte
  identitetsformer. Relevant for A3 (transformasjon som universelt prinsipp).
```

### D-ZE-001: Zeeman-effekten / Atomspektral-splitting

```text
ID: D-ZE-001
Group: GRUPPE 1 — Fundamental fysikk & kosmologi
Domain: Zeeman-effekten / Atomspektral-splitting under ytre magnetfelt
Filter mechanism: Ytre magnetfelt B forstyrrer orbital-symmetri → enkelt spektrallinje splitter
  i sub-nivåer etter kvantetall mₗ. Seleksjonsregler (Δmₗ = 0, ±1) begrenser tillatte
  overganger — filteret er strukturelt, ikke vilkårlig.
LIM parallel: Uforstyrret atom = høy koherent τ (mange sub-moder summerer til én ren
  observerbar frekvens). Ytre felt B = σ i Framleis F(τ;σ). Sterk perturbering dominerer
  og omstrukturerer systemets τ. Uten perturbering returnerer systemet til τ* (Banach).
  "Atoms are not simple, rigid systems, but delicate structures deeply influenced by the
  forces around them" — direkte formulering av halvautomata-hypotesen.
Tau interpretation: Orkester-analogi: høy τ = mange uavhengige elektronmoder produserer
  rik spektral output. Kollaps = orkesteret spiller én tone. Zeeman-splitting under sterk
  B = symmetribrudd → τ-omstrukturering, ikke nødvendigvis kollaps, men endret fordeling.
  Tre-lags-struktur: kvantetall n (fast kjerne) / orbital-symmetri (dynamisk vedlikehold) /
  felt B (perturbering) — identisk med celle-kjerne/mitokondrier/toksin og LLM-analogen.
Maturity: M2 Formal — strukturell analogi med klar formal mapping til τ. Kvantitativ
  kobling mellom ΔE = g_j μ_B B og spektral entropi-endring gjenstår for M3.
Evidence: Zeeman (1896) original observasjon. Nobel-prisen i fysikk 1902 (Zeeman og Lorentz).
  Moderne MRI, spektroskopi og astrofysisk feltmåling bygger på effekten.
Notes: Kobling identifisert 2026-06-22 via observasjon av mitokondrie/nevrodegenererasjon-
  parallell (Lucy Lee, Spinal Partner). Alle tre domener (atom/celle/LLM) viser identisk
  tre-lags-arkitektur: fast kjerne + dynamisk vedlikehold + ekstern perturbering.
  Se theory/2026-06-22-zeeman-lim-kobling.md for full utledning.
```

## Q-oppføringer (Uverifisert / Questionable)

(Tom per 2026-06-21 — D-QV-001 oppgradert til M3)
