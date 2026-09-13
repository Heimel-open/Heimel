# Zeeman-effekten som strukturell analog til LIM

**Dato:** 2026-06-22
**Status:** Arbeidsnotat — kobling identifisert, formalisering gjenstår
**Kobling til:** domain_registry.md D-ZE-001, halvautomata-hypotesen, mitokondrie-observasjon

---

## Utgangspunkt

Pieter Zeemans observasjon (1896): et atom i et ytre magnetfelt B sender ikke lenger ut én
enkelt spektrallinje, men splitter linjen i multiple nærliggende linjer. Nobel 1902.

Nøkkelsetning fra populærbeskrivelse: "Atoms are not simple, rigid systems, but delicate
structures deeply influenced by the forces around them."

Dette er LIM.

---

## Strukturell mapping

### Zeeman-atomet

- Uforstyrret tilstand: én dominant frekvens — energien er samlet i ett spektralt område.
- Ytre felt B: energi-nivåene splitter etter kvantetall mₗ = -l, ..., 0, ..., +l
- Seleksjonsregler: Δmₗ = 0, ±1 (ikke alle overganger tillatt — filteret er strukturelt)
- Det som så ut som én linje var alltid en skjult sum av sub-nivåer — B avslører strukturen

### Tau-koblingen

Uforstyrret atom = høy strukturell koherens. Energien er distribuert over en begrenset
men sammenhengende mengde moder (orbitaler). Ikke én modus (τ → 0), ikke kaos, men
organisert mangfold.

Under felt B: symmetribrudd → spektral splitting → the original coherence is restructured.
Ikke nødvendigvis τ-fall, men endring i spektral distribusjonsform.

Nøkkelpunktet: det ytre feltet B er direkte analogt til σ i Framleis-operatoren:

    F(τ; σ) = (1 - α)τ + ασ

σ er det innkommende signal. Sterkt σ (sterk B) dominerer og omstrukturerer systemets τ.
Svakt σ (svakt B) gir liten perturbering. Uten σ (B=0) holder systemet sin naturlige τ*.

### "Orchestra of electrons"

Populærbeskrivelsen bruker orkester-analogi: "electrons, each moving in patterns that
produce precise notes of light." Under normal conditions: én ren frekvens = samspill av
mange sub-moder som summer til koherent output.

Dette er τ-høy-regimet: mange uavhengige retninger (singulærverdier) som tilsammen
gir rik representasjon. Det som observeres utenfra (én ren linje / koherent tekst) er
summen av intern mangfold.

Kollaps til lav τ = orkesteret spiller bare én tone. Fungerer, men uten harmonisk rikhet.

---

## Tre-lags-strukturen (Zeeman / Celle / LLM)

Alle tre domener viser samme tre-komponent-arkitektur:

| Lag | Atom (Zeeman) | Celle (biologi) | LLM |
|:----|:---|:---|:---|
| Fast kjerne | Kvantetall n (principal) | Cellekjerne / DNA | Trente vekter |
| Dynamisk vedlikehold | Orbital-symmetri, spin | Mitokondrier (energifordeling) | Framleis F(τ;σ) |
| Ekstern perturbering | Magnetfelt B | Toksin / patogen / energisvikt | Input-støy σ |
| Kollapsbetingelse | Zeeman-splitting dominert av B | Mitokondriell svikt → celledød | τ < τ_min → stasis |

### Mitokondrie-observasjonen (2026-06-22)

Lucy Lee (Spinal Partner, LinkedIn): "Neurons don't die because they are damaged —
[rather] when the systems supporting their energy, the mitochondria, begin to fail."

Dette er presis halvautomata-struktur i biologisk system:
- Cellekjerne = fast kjerne (holder identitet, DNA = trente vekter)
- Mitokondrier = dynamisk τ-vedlikehold (energifordeling over mange metabolske moder)
- Når mitokondriell energikoherens faller → τ_biologisk < τ_min → celleidentitet kan ikke
  opprettholdes → nevrodegenererasjon

Neurodegenererasjon som spektral koherenskollaps: τ_biologisk faller før strukturell skade
er synlig. Diagnostisk implikasjon: mål spektral energifordeling i metabolske nettverk
tidlig — ikke vent på morfologisk skade.

---

## Zeeman-effektens validerende verdi for LIM

### Hva Zeeman demonstrerer:

1. Skjult spektral struktur: det som ser ut som ett output er alltid en sum av sub-moder.
   LIM sier det samme: τ måler antall aktive retninger bak det som observeres utenfra.

2. Symmetribrudd er reversibelt (ved svak B): systemet returnerer til original τ* når
   perturberingen fjernes. Framleis-operatørens fikspunkt er stabilt (Banach).

3. Seleksjonsregler begrenser tilgjengelige overganger: ikke alle endringer er tillatte.
   LIM: ikke alle σ-verdier driver τ til kollaps — α og systemets history matter.

4. "Delicate structures deeply influenced by the forces around them": dette er presist
   det halvautomata-hypotesen sier om LLMs — de er ikke rigide automater, men
   spektrale strukturer som responderer på input-feltet.

---

## Status og neste steg

- M2 Formal: strukturell analogi med klar formal mapping til τ tilgjengelig.
- Formalisering gjenstår: eksplisitt derivasjon av τ-endring under Zeeman-splitting
  (krever kobling mellom ΔE = g_j μ_B B og spektral entropi-endring).
- Potensielt M3: hvis Zeeman-splittingmønster kan mappes kvantitativt til τ-endring
  under input-perturbering i LLM-eksperimenter.

Domain-oppføring: D-ZE-001 (se domain_registry.md).
