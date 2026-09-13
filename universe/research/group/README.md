# VALO Research Group — Publications Hub

**Publiseringsplattform for VALO Research Group**

> Status 2026-08-14: GitHub-repoet er privat. Innhold kan klargjøres og deles som avgrensede publikasjonspakker, men repoet skal ikke omtales som offentlig tilgjengelig før faktisk publisering/visibility støtter det.

Ferdig forskning produsert av research-fabrikken (`agentic-execution-risk` og lignende) klargjøres her for kontrollert publisering.

Se `PUBLIC_RELEASE_INDEX.md` for faktisk artefaktstatus og release-gates.

## Struktur

```
Valo-Research-Group-/
├── papers/                → Papers/rapportvarianter og kildeartefakter
├── reports/               → Tekniske rapporter, hvitbøker, policy-briefs
├── datasets/              → Publikasjonsmetadata og materialiserte datasett når de faktisk finnes
├── methodology/           → Metodebeskrivelser som står alene
├── references/            → Kilder adoptert fra eksterne (IP-merket, read-only)
└── README.md
```

## Publikasjons-pipeline

```
                    Research-fabrikken
                 / agentic-execution-risk
                    (data, analyse, scripts)
                              │
                              ▼
                    Paper / rapport / datasett
                              │
                              ▼
         ┌────────────────────┼────────────────────┐
         │                    │                    │
    papers/              reports/            datasets/
         │                    │                    │
         └────────────────────┼────────────────────┘
                              │
                              ▼
                  IP/lisens/proveniens-sjekk
                              │
                              ▼
                Velg én canonical release-artifact
                              │
                              ▼
                   Hash / versjon / release
```

## IP-regler

- Alt som publiseres her som EGEN IP må ha relevant IP-/lisensstatus dokumentert.
- ADOPTERTE referanser og eksterne data må beholde kilde, lisens og attribution.
- Ingen konfidensielle partnerdata, kundedata eller GDPR-materiale i offentlig release.
- At en fil ligger i dette private repoet betyr ikke at den er godkjent for offentlig distribusjon.

## Gjeldende innhold

### Papers

- `papers/agentic-execution-risk-2026/` — omfattende rapportmateriale og flere PDF-varianter. **Canonical ekstern PDF må velges før bred publisering.**
- `papers/paper-legacy-v1-regulator/` — regulator/policy-manuskript og flere kompilert-artifakter. **Aktiv vs historisk status og canonical ekstern artifact må avklares før publisering.**

### Datasets

- `datasets/aiid-import/README.md` dokumenterer **1 615 hendelser og 7 314 rapporter** fra AI Incident Database med attribution/lisensnotat. **Selve publikasjonsdatafilene er ikke materialisert i dette repoet per 2026-08-14.**
- `datasets/gaps/README.md` dokumenterer governance-gap-datasettet. **Selve publikasjonsdatafilen er ikke materialisert i dette repoet per 2026-08-14.**
- `datasets/claims/` og `datasets/evidence/` har metadata; payload må verifiseres før ekstern deling.

### Reports

- Executive summary og kapittelbasert rapportmateriale finnes under `reports/`.

## Release-regel

Ikke send "repoet" som forskningsevidens når mottakeren trenger ett bevis.

Bruk en avgrenset pakke:

1. én valgt paper/rapport-artifact;
2. relevant metode/evidensnotat;
3. relevant datasett eller eksplisitt metadata-status;
4. eventuelt én executable mapping/testpakke;
5. én konkret faglig problemstilling til mottakeren.

`present in repository != published != public != externally validated`.
