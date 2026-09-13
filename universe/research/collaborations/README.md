# valo-research-collaborations

Privat forskningsinstitusjon i repoform — et felles rom for **uavhengige
forskningssamarbeid** mellom Margaret Stokes, Elsa og Njål Solland.

Dette er **ikke** et VALO-produktrepo. Det er et felles forskningsrom,
kildehistorikk og attribusjonslogg der separate IP-er kan møtes uten å
automatisk bli felles IP.

## Den røde tråden

De tre arbeidene møtes naturlig:

- **Margaret:** Hva har standing, og hva er admissible?
- **Elsa:** Hvem har myndighet, innenfor hvilket mandat, tidsrom og omfang?
- **Njål:** Hva kan stabiliseres, autoriseres og faktisk få konsekvens?

```text
Virkelighet og standing
        ↓
Margaret / Aurora-Lens
        ↓
Myndighet, mandat og tid
        ↓
Elsa / Authority Instrumentation
        ↓
Representasjon og stabilisering
        ↓
Tofoo / J-space / Framleis
        ↓
Konkret autorisasjon
        ↓
REHT
        ↓
Konsekvens
```

Forskningsprogrammet:

> **Standing determines what has been established. Authority determines who
> may act. Stabilisation determines what the system proposes. REHT determines
> what consequence may occur now.**

## Struktur

```text
common/                       # spørsmål dere undersøker sammen
  research-principles/
  shared-questions/
  terminology/
  synthesis/
  decision-log/
margaret-stokes/              # Margaret sitt spor (originalt arbeid)
  aurora-lens/
  answerability/
  persistent-standing/
  evidence-admission/
  communication-admissibility/
elsa/                         # Elsa sitt spor (originalt arbeid)
  authority-instrumentation/
  mandate-and-scope/
  temporal-authority/
  revocation/
  human-authority/
njal-solland/                 # Njål sitt spor (originalt arbeid)
  tofoo/
  j-space/
  framleis/
  operational-fixed-points/
  execution-governance/
intersections/                # grenseflater mellom arbeidene
  standing-and-authority/
  admissibility-and-authorisation/
  persistence-and-time/
  identity-mandate-and-consequence/
  aurora-reht-boundary/
adr/                          # arkitektur-beslutningsregistre (felles konklusjoner)
docs/                         # samarbeidsprosedyrer og maler
```

## Eierskapsregler

Felles repo betyr **ikke** felles IP. Hvert spor må ha:

- navngitt opphavsperson
- eksplisitt eierskap
- status: publisert, privat, hypotese eller uavklart
- tillatt bruk
- tydelig skille mellom originalt arbeid og felles syntese

`common/` og `intersections/` skal bare inneholde:

- spørsmål dere undersøker sammen
- grenseflater mellom arbeidene
- gjensidige vurderinger
- synteser som er tydelig kreditert
- åpne problemer
- arkitektoniske konsekvenser

## Rettigheter og arbeidsform

- Hver forsker arbeider gjennom egen GitHub-identitet — ingen delte brukerkontoer.
- Signerte commits der det er praktisk.
- Alle vesentlige endringer gjennom pull request.
- Tydelig forfatter og eier øverst i hvert dokument.
- Eget felt for «originalt arbeid», «kritikk», «felles syntese» og «VALO-anvendelse».
- Ingen omskriving av andres arbeid uten synlig diff og godkjenning.
- ADR-er for felles konklusjoner.
- Tags eller releases ved avtalte forskningsmilepæler.

## Branch- og PR-modell

```text
margaret/*
elsa/*
njal/*
shared/*
```

En felles syntese går ikke direkte på `main`. Den opprettes som PR og
godkjennes av alle hvis den beskriver deres arbeid.

Historikken kan dermed vise:

```text
Margaret introduserte påstanden
→ Njål foreslo arkitektonisk syntese
→ Elsa utfordret autoritetsdelen
→ Margaret presiserte standing
→ felles formulering ble godkjent
```

## Dokumentmal

Sjå `docs/document-template.md`. Felt per dokument:

```text
Title:
Author:
Original IP owner:
Contributors:
Status: hypothesis / draft / reviewed / accepted
Based on:
Changes from prior version:
Permitted use:
Related synthesis:
```

## Roller

- **Margaret Stokes** og **Elsa** er selvstendige forskere — ikke ansatte eller leverandører.
- **Njål Solland** eier VALO-repoene og er kanonisk eier av `njal-solland/` og `docs/`.
- Felles konklusjoner besluttes i `adr/` med navngitte godkjennere.
