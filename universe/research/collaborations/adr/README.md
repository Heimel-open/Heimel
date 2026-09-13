# ADR — arkitektur-beslutningsregister

Felles konklusjoner og arkitektoniske konsekvenser besluttes her, med
navngitte godkjennere. Ingen syntese beskriver andres arbeid uten deres
godkjenning.

## Format

Hver ADR bruker malen i `docs/document-template.md` og legger til:

```text
Decision:
Decision makers: (navn, navn, ...)
Status: proposed / accepted / superseded
Superseded by: ADR-XXXX
```

## Konvensjon

- `ADR-XXXX-short-name.md` — sekvensiell nummerering.
- Status `proposed` til alle involverte har godkjent.
- `superseded` brukes når en nyere konklusjon erstatter en eldre.
