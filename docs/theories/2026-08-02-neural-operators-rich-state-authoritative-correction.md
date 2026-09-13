# Neural operators, rich state og autoritativ korreksjon

Dato: 2026-08-02  
Status: Kanonisk metodebro  
Modenhet: M1 konseptuell / M2 formelt skjema  
Kilde: Kaushik Bhattacharya, *Multiscale modeling of materials and neural operators*, arXiv:2605.08466v1, 8. mai 2026.

## Hva artikkelen faktisk viser

Artikkelen handler om multiskalamodellering i materialfysikk. Bidraget er ikke en ny generell teori om organisasjoner eller AI-governance. Den viser tre metodiske mønstre som er direkte relevante for Tofoo og VALO:

1. En modell for historikkavhengige systemer bør lære en intern tilstand som komprimerer den delen av historikken som er relevant for neste respons.
2. En representasjon bør beskrive den underliggende sammenhengen, ikke låses til én bestemt tidsoppløsning, gridstørrelse eller diskretisering.
3. Når maksimalfeil betyr mer enn gjennomsnittsfeil, bør en lært surrogate produsere en rik mellomtilstand som sendes gjennom en autoritativ metode før sluttresultatet godtas.

Dette er ekstern metodisk støtte. Det er ikke empirisk validering av Φ-loven, Tofoo, VAIG, REHT eller RACS.

## Forståelsen vi adopterer

### 1. Historikk blir operativ gjennom tilstand

I den recurrent neural operatoren beskrives responsen ved en lært tilstandsvariabel ξ(t):

```text
respons(t) = ψ_response(input(t), ξ(t))
dξ/dt      = ψ_state(input(t), ξ(t))
```

Tilstanden er ikke definert på forhånd. Den læres fra data som den minste representasjonen som bærer beslutningsrelevant historikk videre.

Tofoo-tolkningen er avgrenset:

```text
historikk H_t → latent tilstand ξ_t → neste mulige respons
```

Dette støtter hypotesen om at identitet og forståelse ikke ligger i ett isolert utsagn, men i den vedlikeholdte tilstanden mellom hendelser. Det er en strukturell parallell til Framleis og Synapse, ikke et bevis for dem.

### 2. Bevar fenomenet på tvers av representasjoner

Vanlige nevrale nettverk kan lære både fenomenet og den konkrete diskretiseringen de ble trent på. Neural operators søker i stedet å lære en funksjon-til-funksjon-relasjon som kan brukes ved andre oppløsninger.

Governance-analogen er:

```text
samme forretningshandling
→ agentkall
→ verktøykall
→ workflow
→ transaksjon
→ institusjonell konsekvens
```

Styringssemantikken må overleve skiftet i granularitet. Mandat, evidens, konsekvens og ansvar kan ikke endre mening bare fordi handlingen beskrives på et annet teknisk nivå.

Kanonisk regel:

> Governance skal være representasjons- og granularitetsuavhengig, men konsekvenssensitiv.

### 3. Rik mellomtilstand er bedre enn et direkte sluttall

I DFT-eksemplet ga direkte prediksjon av total energi lav gjennomsnittsfeil, men for høy maksimalfeil. Modellen ble bedre da den lærte fire underliggende felt og atomposisjoner, og disse ble brukt som startpunkt for én autoritativ self-consistent-field-iterasjon.

Metodemønsteret er:

```text
kompleks input
→ lært rik tilstand
→ autoritativ korreksjon
→ sluttresultat
```

VALO-adopsjonen er:

```text
modell/agent produserer forslag + tilstand + evidens
→ VAIG evaluerer kvalitet, usikkerhet, grenser og mangler
→ REHT avgjør om handlingen kan klareres her og nå
→ RACS håndhever utfallet
→ receipt dokumenterer hva som faktisk skjedde
```

Surrogaten kan redusere kostnad og bringe systemet nær en riktig løsning. Den får ikke attestere sin egen produksjonsklarhet og får ikke execution authority.

### 4. Gjennomsnittsfeil er utilstrekkelig ved høy konsekvens

Artikkelen skiller mellom god gjennomsnittsytelse og kontroll på maksimalfeil. For VALO betyr dette at følgende ikke er nok alene:

- gjennomsnittlig modellscore
- samlet accuracy
- gjennomsnittlig confidence
- gjennomsnittlig kostnad eller latency

Admissibility må også vurdere:

- tail risk
- boundary error
- verste plausible konsekvens
- lokal diskontinuitet
- out-of-distribution-adferd
- om feil kan reverseres

Kanonisk regel:

> Operasjonell admissibility bestemmes ikke av gjennomsnittsytelse når en enkelt feil kan dominere konsekvensen.

## Formell VALO-bro

La:

- `x_t` være nåværende input eller foreslått handling
- `H_t` være relevant historikk
- `ξ_t = S(H_t)` være komprimert beslutningsrelevant tilstand
- `ê_t` være evidenspakken
- `m_t` være mandat og autoritet
- `c_t` være konsekvensmodellen
- `ŷ_t` være modellens forslag

Da:

```text
ξ_t  = S(H_t)
ŷ_t  = G(x_t, ξ_t)
v_t  = VAIG(x_t, ξ_t, ê_t, c_t)
r_t  = REHT(ŷ_t, v_t, m_t, c_t)
a_t  = RACS(r_t)
```

Der `a_t` bare kan føre til utførelse når den autoritative kjeden tillater det.

Den lærte modellen `G` er en surrogate. `VAIG → REHT → RACS` er ikke en etterbehandling av samme modell, men en separat kontroll- og myndighetskjede.

## Krav som adopteres

1. Stateful vurdering: VAIG- og REHT-input skal kunne bære relevant historikk eller en verifiserbar state digest, ikke bare siste modellrespons.
2. Granularitetsinvarians: policy og mandat skal uttrykkes slik at samme handling vurderes konsistent på tvers av agent-, workflow- og transaksjonsnivå.
3. Rich-state output: Høykonsekvensmodeller bør levere relevante mellomrepresentasjoner, evidens og usikkerhet, ikke bare et sluttforslag.
4. Autoritativ korreksjon: Deterministiske eller formelt styrte mekanismer skal fullføre eller avvise høykonsekvensbeslutningen.
5. Tail-aware evals: VAIG-evaluering skal inkludere maksimalfeil, boundary cases og konsekvensvektede feil, ikke bare middelverdier.
6. Ingen selvattestering: Den samme modellen eller agenten kan ikke både produsere forslaget og etablere execution authority.
7. Sporbar skalabro: Receipts skal kunne vise hvilken representasjon, granularitet og state-versjon vurderingen bygget på.

## Hva vi ikke adopterer

- At neural operators i seg selv løser governance.
- At latent state automatisk er forståelig, sann eller normativt riktig.
- At oppløsningsuavhengighet betyr kontekstuavhengighet.
- At én autoritativ iterasjon alltid er nok utenfor det konkrete DFT-eksemplet.
- At ekstern suksess i materialfysikk validerer Φ-loven eller VALOs produksjonsarkitektur.

## Falsifiserbare interne hypoteser

H1. Rich-state + autoritativ korreksjon reduserer boundary- og tail-feil sammenlignet med direkte sluttprediksjon på samme workflow.

H2. En policy uttrykt på kanonisk handlingsnivå gir mer konsistente REHT-utfall når samme handling deles opp i ulike agent- og workflow-granulariteter.

H3. Stateful vurdering reduserer feil klarering i historikkavhengige workflows sammenlignet med vurdering av siste melding alene.

H4. State digests og representasjonsmetadata gjør det mulig å reprodusere og forklare beslutningsforskjeller som ellers fremstår som model drift.

## Kanonisk formulering

> En styrt AI-arkitektur skal ikke redusere en kompleks prosess direkte til en beslutning. Den skal bevare beslutningsrelevant tilstand mellom hendelser og på tvers av skalaer, før en separat autoritativ mekanisme avgjør om handlingen kan skje.

## Arkitekturplassering

- Tofoo / Framleis: teori om vedlikeholdt tilstand over tid.
- Synapse: hypotesen om at mening oppstår i overgangen og relasjonen mellom hendelser.
- VAIG: vurdering av rik tilstand, evidens, usikkerhet, boundary error og tail risk.
- REHT: autoritativ klarering av handling her og nå.
- RACS: håndheving av klareringsutfallet.
- Receipts: bevis på state-versjon, representasjon, vurdering, myndighet og faktisk utfall.

Dette er ikke et nytt produkt, nytt styringslag eller ny execution authority.
