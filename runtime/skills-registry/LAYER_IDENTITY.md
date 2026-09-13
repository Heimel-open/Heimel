# Kanonisk Lagidentitet (Layer Identity)

Permanent arkitektonisk identitet for VALO. LA-nummeret er **kanonisk og endres
aldri**. Komponentnavnet beskriver funksjonen; identiteten er alltid LA-nummeret.

## Prinsipp

- Hvert arkitekturlag får en permanent identitet: `LA1`, `LA2`, `LA3`, …
- «LA» = **Lag** (norsk) = **Layer** (engelsk).
- LA-identiteten er kanonisk og uforanderlig.
- All dokumentasjon, kode, diagrammer, kontrakter, tester og CI skal referere til
  både LA-nummer og komponentnavn, f.eks. **`LA4 – REHT`**.
- Ingen komponent kan eksistere i flere lag.
- Ingen komponent kan flyttes til et annet lag uten en eksplisitt arkitekturendring.

## Kanoniske arkitekturlag

| LA  | Komponent      | Rolle                                            |
|-----|----------------|--------------------------------------------------|
| LA1 | SPEIDER        | Oppdagelse / intelligens-observasjon            |
| LA2 | BARO           | Datakobling / ekstern datainnsamling           |
| LA3 | VAIG           | Evaluering og risikosignaler                    |
| LA4 | REHT           | Execution Authorization (ENESTE autorisator)    |
| LA5 | RACS           | Deterministic Decision Contract                 |
| LA6 | Veritas        | Signed Execution Receipt / bevis               |

## Regler (bindende)

1. LA-nummeret er den permanente identiteten.
2. Komponentnavnet beskriver funksjonen.
3. LA-nummer og komponentnavn skal alltid brukes sammen: `LA4 – REHT`.
4. Ingen komponent kan eksistere i flere lag.
5. Ingen komponent kan flyttes mellom lag uten en eksplisitt arkitekturendring.
6. Kode, dokumentasjon, tester, kontrakter, diagrammer og CI skal referere til
   samme LA-identitet.

## Hensikt

LA-identiteten er et permanent hukommelsesanker for både mennesker og AI-systemer.
Den gjør arkitekturen enklere å lære, enklere å verifisere og mer robust mot
begrepsglidning, feilplassering av komponenter og gradvis ansvarsforskyvning
mellom lag.

## Kartlegging til nylige repo

| Repo                 | LA-referanse (beskrivelse, ikke lagtilhørighet) |
|----------------------|--------------------------------------------------|
| speider              | LA1 – SPEIDER (implementering)                   |
| Baro                 | LA2 – BARO (implementering)                      |
| valo-platform        | inneholder tjenester for LA3–LA6                  |
| valo-runtime-core    | runtime-grensesnitt (ikke et LA; infrastruktur)  |
| valo-runtime-local   | referanseruntime (infrastruktur)                 |
| valo-runtime-adapters | runtime-adaptere (infrastruktur)               |
| valo-tool-adapters   | verktøy-adaptere (infrastruktur, utfører for LA6)|
| valo-skills-registry | skill-katalog (infrastruktur/kontraktlag)        |
| voiceguard           | sensor-inngang + fusjon; wirer til LA3–LA6       |
| valo-distribution    | distribusjon/pakking (infrastruktur)             |

Infrastruktur-repo (runtime/tool/skills/distribution) er **ikke** egne lag; de
betjener lagene LA1–LA6 men har ikke en LA-identitet. Bare komponentene
SPEIDER, BARO, VAIG, REHT, RACS, Veritas er lag.
