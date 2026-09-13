# Dokumentmal

Felt per dokument i dette repoet. `Status` endres kun av opphavspersonen
eller ved godkjent felles syntese.

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

## Retningslinjer

- `Title`: kort, presis beskrivelse av påstanden eller arbeidet.
- `Author`: hvem som skrev dette dokumentet.
- `Original IP owner`: hvem som eier det originale arbeidet (uavhengig av felles repo).
- `Contributors`: andre som bidro — de får ikke automatisk IP.
- `Status`: `hypothesis` (antakelse), `draft` (arbeid pågår), `reviewed`
  (lest og vurdert), `accepted` (godkjent felles konklusjon).
- `Based on`: referanse til kilder eller tidligere dokumenter.
- `Changes from prior version`: hva som faktisk endret seg siden forrige versjon.
- `Permitted use`: hva innholdet kan brukes til (f.eks. "kun intern
  forskning", "kan inngå i VALO-anvendelse", "kun etter avtale").
- `Related synthesis`: hvilke `intersections/`- eller `adr/`-dokumenter
  dette henger sammen med.

## Eget felt for innholdstype

Legg inn tydelig merking:

- `ORIGINALT ARBEID` — opphavspersonens eget bidrag.
- `KRITIKK` — vurdering av et annet arbeid, adressert til opphavspersonen.
- `FELLES SYNTESE` — kombinert resultat av flere arbeider, tydelig kreditert.
- `VALO-ANVENDELSE` — konsekvenser for VALO/REHT-arkitekturen (input, ikke autoritet).

## Skille originalt vs felles

`common/` og `intersections/` skal kun inneholde:

- spørsmål dere undersøker sammen
- grenseflater mellom arbeidene
- gjensidige vurderinger
- synteser som er tydelig kreditert
- åpne problemer
- arkitektoniske konsekvenser

Originalt arbeid ligger i hver persons egen mappe.
