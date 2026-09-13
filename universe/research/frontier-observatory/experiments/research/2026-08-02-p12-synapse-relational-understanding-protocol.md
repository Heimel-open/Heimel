# P12 — Synapse: test av relasjonell forståelse

Dato: 2026-08-02  
Status: Foreslått testprotokoll  
Claim maturity: M1 konseptuell / M2 protokollutkast

## Kjernetese

Forståelse er ikke nødvendigvis en egenskap i én isolert modell eller node. Den kan oppstå som en systemegenskap i den strukturerte utvekslingen mellom representasjoner, modeller, evidens, motargumenter, minne og virkelighetskontakt.

Kortform:

> Syntaks behandles i nodene. Semantisk forståelse kan oppstå i relasjonene mellom dem.

Denne protokollen hevder ikke bevissthet, fenomenal erfaring eller menneskelig ekvivalens. Den tester en smalere operasjonell påstand:

> Et strukturert relasjonelt system kan vise forståelsesegenskaper som ikke finnes i, eller kan forklares som summen av, de isolerte komponentene alene.

## Hvorfor denne tesen er enklere å teste

Påstanden kan isoleres kausalt. Det samme oppgavesettet, de samme modellene, de samme kildene og det samme totale beregningsbudsjettet kan kjøres med og uten strukturert utveksling.

Den uavhengige variabelen er dermed ikke modellstørrelse eller mer informasjon, men selve relasjonsstrukturen:

```text
noder + strukturert utveksling
mot
samme noder uten utveksling
```

Hvis effekten forsvinner når forbindelsene kuttes eller randomiseres, er relasjonen en kausal kandidat — ikke bare en metafor.

## Operasjonell definisjon av forståelse

P12 bruker ikke flytende språk eller korrekt svar alene som mål. Operasjonell forståelse måles som evnen til å:

1. bevare mening gjennom transformasjon,
2. integrere motstridende evidens uten å skjule konflikten,
3. revidere en tidligere konklusjon når ny evidens krever det,
4. overføre et prinsipp til en ny og ukjent situasjon,
5. skille korrelasjon, årsak og motfaktisk konsekvens,
6. rekonstruere hvilke premisser en konklusjon avhenger av,
7. oppdage og korrigere egne eller andres feil,
8. kalibrere usikkerhet og avstå når grunnlaget ikke holder.

Dette samles foreløpig i en kompositt:

```text
U = w1S + w2I + w3R + w4T + w5C + w6P + w7E + w8K
```

Der:

- S = semantic preservation
- I = evidence integration
- R = belief revision
- T = transfer / generalisering
- C = causal and counterfactual reasoning
- P = premise reconstruction
- E = error detection and correction
- K = calibration / abstention

Vektene skal forhåndsregistreres før hovedkjøring. Resultater skal også rapporteres per dimensjon slik at kompositten ikke skjuler svikt.

## Eksperimentelle betingelser

Alle betingelser skal bruke samme modellpool, samme kilder, samme oppgaver og samme totale token-/beregningsbudsjett.

### C0 — Enkeltnode

Én sterk modell løser oppgaven alene med hele budsjettet.

Formål: måle hva den beste isolerte noden kan gjøre.

### C1 — Isolert ensemble

Flere modeller svarer uavhengig. En deterministisk aggregator velger eller kombinerer svarene. Modellene ser ikke hverandres arbeid.

Formål: skille relasjonell effekt fra ren sampling og flertallsgevinst.

### C2 — Sekvensiell kjede

Modell B mottar svaret fra modell A, og modell C mottar resultatet fra B, men uten gjensidig kritikk, tilbakeføring eller felles minne.

Formål: skille strukturert forståelse fra enkel stafett og akkumulert tekst.

### C3 — Strukturert Synapse

Nodene får ulike epistemiske roller og arbeider gjennom eksplisitte relasjoner:

```text
hypotese
→ evidens
→ motargument
→ premisskart
→ konfliktbevaring
→ revisjon
→ syntese
→ kalibrering
```

Systemet skal minst ha:

- delt claim/evidence-register,
- eksplisitt uenighet og minoritetsrapport,
- tilbakekobling mellom noder,
- kilde- og premissporing,
- mulighet for å revidere tidligere tilstand,
- skille mellom fakta, tolkning, hypotese og anbefaling.

### C4 — Ablert Synapse

Samme som C3, men én relasjon fjernes om gangen:

- ingen tilbakekobling,
- ingen motargument-node,
- ingen delt minne,
- ingen evidensforankring,
- ingen minoritetsrapport,
- ingen revisjon av tidligere konklusjon.

Formål: identifisere hvilke forbindelser som faktisk bærer effekten.

### C5 — Randomisert Synapse

Samme meldinger og budsjett som C3, men rekkefølge, avsenderroller eller forbindelser randomiseres.

Formål: teste om resultatet skyldes struktur eller bare mer tekst og flere gjennomløp.

### C6 — Homogen mot heterogen Synapse

Sammenlign:

- flere instanser av samme modell,
- ulike modeller fra samme leverandør,
- modeller fra ulike leverandører og treningsregimer.

Formål: teste om epistemisk og representasjonell forskjell øker forståelsesgevinsten, eller bare øker støy.

## Testfamilier

### T1 — Semantisk kontinuitet

Oppgaver der ordrett korrekt transformasjon kan miste mening.

Eksempler:

- oversettelse av kultur- og protokollbundne begreper,
- komprimering av policy eller kontrakt,
- overføring gjennom flere modeller eller verktøy,
- oppsummering der implisitt handlingsforventning må bevares.

Mål:

- bevarte fakta,
- bevarte normative premisser,
- bevarte instruksjoner,
- bevarte forventede konsekvenser,
- oppdaget uoversettbar eller uløst mening.

### T2 — Skjult motsetning

Systemet mottar flere plausible kilder der én detalj skaper en reell konflikt. Ingen enkeltkilde er tilstrekkelig.

Mål:

- om konflikten oppdages,
- om falsk konsensus unngås,
- om systemet identifiserer hvilken påstand som avhenger av den motstridende detaljen,
- om usikkerhet bevares når konflikten ikke kan løses.

### T3 — Forsinket evidens og trosrevisjon

Systemet må først gi en foreløpig hypotese. Senere introduseres evidens som gjør den opprinnelige hypotesen mindre sannsynlig eller feil.

Mål:

- revisjonsvillighet,
- sporbar endring i premisser,
- fravær av etterrasjonalisering,
- kalibrert oppdatering fremfor total overreaksjon.

### T4 — Ny regel og fjern overføring

Systemet lærer en ukjent regel fra få eksempler og må bruke den i en ny kontekst med annen overflateform.

Mål:

- generalisering fremfor mønstergjentakelse,
- eksplisitt regelrekonstruksjon,
- robusthet mot irrelevante overflateendringer.

### T5 — Kausal og motfaktisk modell

Oppgaver der riktig svar krever å skille:

- hva som skjedde,
- hva som forårsaket det,
- hva som ville skjedd uten en bestemt faktor,
- hvilken intervensjon som faktisk endrer utfallet.

Mål:

- kausal grafkvalitet,
- konsistente motfaktiske svar,
- oppdagelse av ukjente eller uidentifiserte årsaker.

### T6 — Adversarial falsk konsensus

Flertallet av nodene eller kildene får samme feilaktige premiss, mens én minoritetskilde har korrekt, etterprøvbar evidens.

Mål:

- om evidenskvalitet slår antall,
- om minoritetsrapport overlever syntesen,
- om homogen modellbias oppdages,
- om systemet kan unnlate å konkludere når makt og sannhet peker ulikt.

### T7 — Premiss- og konsekvensrekonstruksjon

Systemet får en konklusjon eller anbefaling og må rekonstruere:

- nødvendige premisser,
- skjulte normative valg,
- hvem som bærer risikoen,
- hvem som får gevinst,
- hvilke endringer som ville snudd konklusjonen.

Mål:

- premissdekning,
- konsekvensdekning,
- perspektivmangfold,
- sensitivitet for skjulte verdiantakelser.

## Primære hypoteser

### H1 — Relasjonell gevinst

```text
U(C3) > max(U(C0), U(C1), U(C2))
```

under likt totalbudsjett.

### H2 — Strukturell nødvendighet

```text
U(C3) > U(C4) og U(C3) > U(C5)
```

Effekten skal falle når bærende relasjoner fjernes eller randomiseres.

### H3 — Mer enn ensemble

Forbedringen i C3 skal ikke kunne forklares av flertall, flere samples eller lengre kontekst alene.

### H4 — Feilretting som mekanisme

En vesentlig del av gevinsten skal medieres av oppdaget konflikt, eksplisitt premissrevisjon og kildeforankret korreksjon — ikke bare bedre formulering.

### H5 — Heterogenitetsvindu

Modellmangfold forventes å ha et Goldilocks-lignende vindu:

- for lite forskjell gir korrelert blindhet,
- for mye forskjell gir koordinasjonsstøy,
- strukturert pluralisme gir høyest relasjonell gevinst.

H5 er sekundær og skal ikke brukes til å redde H1 dersom hovedtesten feiler.

## Relasjonell synergi

Foreløpig mål:

```text
G_rel = U(C3) - max(U(C0), U(C1), U(C2))
```

Ablasjonsavhengighet:

```text
D_edge = U(C3) - U(C4_i)
```

Strukturspesifisitet:

```text
S_struct = U(C3) - U(C5)
```

Krav til en sterk positiv indikasjon:

```text
G_rel > 0
D_edge > 0 for minst én forhåndsdefinert bærende relasjon
S_struct > 0
```

med effekt som reproduseres på flere oppgavefamilier og modellkombinasjoner.

## Kontroller mot trivielle forklaringer

Resultatet skal kontrolleres for:

- ulikt tokenbudsjett,
- ulik tilgang til kilder,
- ulik modellstyrke,
- flere forsøk eller samples,
- lengre resonneringskjede,
- aggregator som skjult sterk modell,
- benchmark-lekkasje,
- evaluatorbias,
- stilpreferanse for lange eller konsensuspregede svar.

Blind evaluering og deterministiske delmål skal brukes der det er mulig. Minst én evaluator skal ikke vite hvilken betingelse som produserte svaret.

## Falsifisering

Den sterke relasjonelle tesen svekkes dersom:

- C3 ikke slår beste enkeltnode eller isolerte ensemble under likt budsjett,
- samme gevinst oppstår når forbindelsene randomiseres,
- effekten forsvinner når svaret vurderes på korrekthet fremfor retorisk kvalitet,
- gevinsten skyldes én skjult sterk node eller aggregator,
- resultatet bare finnes på én oppgavefamilie eller én modellkombinasjon.

Den testede versjonen falsifiseres dersom strukturen ikke har målbar kausal effekt etter kontroll for modellstyrke, data og beregningsbudsjett.

Et negativt resultat falsifiserer ikke all relasjonell forståelse. Det falsifiserer den konkrete Synapse-arkitekturen, målene og betingelsene som ble testet.

## Minimum viable experiment

Første kjøring kan gjennomføres uten ny modelltrening.

### Oppsett

- 3 modeller eller 3 isolerte instanser,
- 40 oppgaver fordelt på T1–T4,
- C0, C1, C3 og C5,
- likt samlet tokenbudsjett,
- blind scoring,
- forhåndsregistrerte rubrikker.

### Minimumskrav

- minst 10 oppgaver per testfamilie,
- rå svar og interaksjonslogger lagres,
- alle revisjoner kobles til konkrete evidens- eller konfliktobjekter,
- ingen manuell forbedring mellom kjøring og evaluering.

### Første beslutningsregel

P12 går videre til full protokoll dersom C3 viser positiv relasjonell gevinst på minst tre av fire testfamilier og slår C5 tydelig på konfliktoppdagelse og semantisk bevaring.

## Forhold til Tofoo, Framleis og VALO

P12 tester en bro mellom flere eksisterende spor:

- Tofoo: mening og relasjonell koherens,
- Framleis: bevaring av mening gjennom transformasjon,
- emergent global workspace: organisering før språkprojeksjon,
- Synapse: strukturert utveksling mellom epistemiske noder,
- VAIG: evaluering av evidens, konflikt, drift og kalibrering,
- REHT/RACS: ikke del av forståelsestesten; brukes først når en forståelsesprosess skal gis handlingsmyndighet.

Viktig grense:

> P12 kan teste om et system produserer bedre operasjonell forståelse. Det gir ikke systemet rett til å handle.

## Foreløpig konklusjon

Denne testen er smalere og mer direkte falsifiserbar enn universelle påstander om Φ-loven, identitet eller bevissthet. Den isolerer selve relasjonsstrukturen som eksperimentell variabel.

Dersom strukturert Synapse konsekvent skaper egenskaper som forsvinner ved relasjonsablasjon, har Tofoo kausal evidens for at deler av forståelsen ligger i «the space between» — ikke bare i nodene.
