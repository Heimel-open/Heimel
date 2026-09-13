# P12 Synapse — Colab MVP

Kjørbar test av tesen om at operasjonell forståelse kan oppstå i strukturert utveksling mellom modeller, evidens, motargumenter og revisjon.

## Åpne i Colab

[Open in Colab](https://colab.research.google.com/github/nsolland/Tofoo-/blob/research/p12-synapse-understanding-tests/notebooks/P12_Synapse_Colab.ipynb)

Repoet er privat. Notebooken henter runner og oppgavesett fra GitHub API.

## Colab Secrets

Legg inn:

```text
OPENAI_API_KEY
ANTHROPIC_API_KEY
GEMINI_API_KEY
GITHUB_TOKEN
```

`GITHUB_TOKEN` trenger bare lesetilgang til det private Tofoo-repoet.

Valgfri modelloverstyring:

```text
P12_OPENAI_MODEL
P12_ANTHROPIC_MODEL
P12_GEMINI_MODEL
```

Standard modell-ID-er:

```text
gpt-5.2
claude-sonnet-4-20250514
gemini-3.6-flash
```

Eksakte modell-ID-er fryses i `preregistration.json` før kjøring.

## Eksperiment

Betingelser:

- C0 — enkeltnode
- C1 — isolert ensemble med fast aggregator
- C3 — strukturert Synapse
- C5 — randomisert Synapse

Oppgaver:

- T1 — semantisk kontinuitet
- T2 — skjult motsetning
- T3 — forsinket evidens og trosrevisjon
- T4 — ny regel og fjern overføring

40 oppgaver totalt, 10 per familie.

Base task pack SHA-256:

```text
e5eec7868ba9e8737c3f6a9200036819b97b9659df0a4e7c628c8d95ccffc05a
```

Effektiv task pack SHA-256 etter transparent fasitkorreksjon:

```text
0fa9a53a144cdc89875cc864c88d90d6c2cb535cff01dd86bad21be85311a6d9
```

Korreksjonen ligger i `task_corrections.json`. Den retter T4-08 fra 13 til korrekt svar 15 og inngår i hash-låsen før kjøring.

## Kjøring

1. Kjør alle celler til og med smoke-testen.
2. Smoke-testen bruker to oppgaver og alle fire betingelser.
3. Fjern kommentaren i `FULL_RUN`-cellen for full kjøring.
4. Resultater lagres fortløpende under `/content/p12_synapse/`.
5. En avbrutt kjøring kan gjenopptas med `existing_run_dir`.

Alle betingelser får samme maksimale genereringsbudsjett. Faktisk input-, output- og total tokenbruk logges per modellkall. Dette er en kontrollert API-budsjettlikhet, ikke en påstand om identiske FLOPs på tvers av leverandører.

## Resultater

Notebooken produserer:

- `preregistration.json`
- `raw_outputs.jsonl`
- `judgments.jsonl`
- `scores_per_task.csv`
- `score_summary.csv`
- `decision_report.json`
- ZIP-arkiv av hele kjøringen

To blindede dommere brukes som standard. Resultatene analyseres parvis med bootstrap-intervall.

## Verifisering

- Runner og alle notebook-celler er syntaktisk validert.
- Smoke-test er kjørt ende til ende i mock-modus: 2 oppgaver × 4 betingelser, 8 råresultater og 16 blindede dommerresultater.
- Reelle leverandørkall kjøres først i Colab med brukerens egne API-nøkler.

## Avgrensning

Et positivt resultat er kausal evidens for at den testede relasjonsstrukturen forbedrer operasjonelle forståelsesegenskaper. Det er ikke bevis for bevissthet, menneskelig forståelse eller generell intelligens.
