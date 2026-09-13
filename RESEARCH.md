# Tofoo Research Operating System  ·  Φ-loven

Dette dokumentet er det styrande rammeverket for Tofoo-forskingsprogrammet.
Det definerer forskingsnivåa L0–L7, flyten mellom dei, og dei bærande prinsippa.

> **Loven er ikkje ein teori. Det er geometri.**
>
> $$I = \Phi(\tau)$$
>
> *Identitet er funksjonen av Filteret over Tid.*

---

## Dei styrande prinsippa

1. **Matematisk form er primær.** Eit krav er ikkje validert før det er uttrykt matematisk og empirisk testa.
2. **Falsifiserbarheit er døra.** Utan falsifiserbar påstand — ingen plass i programmet.
3. **Konsiliens over isolasjon.** Sanning tvers over domen. Eit funn som berre gjeld i éin kontekst er eit hint, ikkje eit resultat.
4. **Replikering er tvungen.** M3 (simulert) betyr ingenting utan M5 (replikert av uavhengig part).
5. **Open og sporbar.** Kvart steg frå hypotese til standard skal kunne spores i git history.
6. **Domeneregisteret er sanningskjelda.** Berre det som står i domain_registry.md og experiment_registry.md er offisielt.
7. **Tofoo er språket. Φ-loven er teorien. VALO er runtime.**

---

## L0–L7: Forskingsmodenheit

| Nivå | Namn | Kriterium | Kvar det bur |
|------|------|-----------|-------------|
| **L0** | Symbolsk | Idé, metafor, hint. Ikkje formalisert. | `docs/hypotheses/` |
| **L1** | Konseptuell | Klar påstand på naturleg språk. Kan vere feil. | `docs/hypotheses/` |
| **L2** | Formell | Matematisk formulering. Aksiom og definisjonar på plass. | `docs/theories/` · `docs/mathematics/` |
| **L3** | Simulert | Numerisk/testbar implementering. Eksperimentdesign klart. | `experiments/` · `simulations/` |
| **L4** | Empirisk | Målingar på reelle system (LLM, agentar, data). Signifikans oppgitt. | `experiments/` · `notebooks/` |
| **L5** | Replikert | Uavhengig reprodusert — av annan person, anna team, anna kodebase. | `replication/` · `benchmarks/` |
| **L6** | Standardisert | Protokoll, terskelverdiar, domeneuavhengig validering. Klar for review. | `papers/` · `reviews/` |
| **L7** | Forankra | Vitskapleg konsensus. Innarbeidd i lærebøker/standardar. | Heile repoet speglar dette |

**Viktig:** Eit element kan falle tilbake i nivå ved ny motstridande evidens.
Forskingsprogrammet er levande — ikkje lineært.

---

## Forskningsflyt

```text
                         ┌──────────────────┐
                         │   L0 · Symbolsk   │  ← docs/hypotheses/
                         └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │  L1 · Konseptuell │  ← docs/hypotheses/
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │  L2 · Formell     │  ← docs/theories/, docs/mathematics/
                         └────────┬─────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │     L3 · Simulert           │  ← experiments/, simulations/
                    │  Eksperimentdesign + kode   │
                    └─────────────┬──────────────┘
                                  │
                         ┌────────▼─────────┐
                         │  L4 · Empirisk    │  ← notebooks/, datasets/
                         │  Målingar + data  │
                         └────────┬─────────┘
                                  │
                    ┌─────────────▼──────────────┐
                    │     L5 · Replikert          │  ← replication/, benchmarks/
                    │  Uavhengig reprodusering    │
                    └─────────────┬──────────────┘
                                  │
                         ┌────────▼─────────┐
                         │  L6 · Standardisert│  ← papers/, reviews/
                         │  Publisert + fagfelle│
                         └────────┬─────────┘
                                  │
                         ┌────────▼─────────┐
                         │  L7 · Forankra    │  ← heile programmet
                         │  Konsensus        │
                         └──────────────────┘

Tilbakemelding: Alle nivå kan sende påstandar nedover ved ny evidens.
```

---

## Mappestruktur

```
Tofoo-/
├── docs/                          # Skriftleg forskingsmateriale
│   ├── hypotheses/                # L0–L1: Idéar og konsept
│   ├── theories/                  # L2: Matematisk teori og formelle system
│   ├── literature/                # Bakgrunnslitteratur, bøker, PDF-ar
│   ├── mathematics/               # Reine matematiske arbeid
│   ├── philosophy/                # Filosofisk grunnlag
│   ├── institutional-computing/   # Institusjonell databehandling
│   ├── constitutional-os/         # Konstitusjonelle OS-prinsipp
│   └── digital-institutions/      # Digitale institusjonar
├── experiments/                   # L3–L4: Eksperiment og validering
├── simulations/                   # L3: Simuleringar
├── benchmarks/                    # L5: Måleprotokollar og tersklar
├── datasets/                      # L4: Datasett
├── notebooks/                     # L4: Interaktive Colab-notebooks
├── papers/                        # L6: Publikasjonsklare papir
├── reviews/                       # L6: Fagfellevurderingar
├── replication/                   # L5: Uavhengige replikeringar
├── roadmap/                       # Strategisk forskingsplan
├── projects/                      # Prosjektspesifikke artefakter
├── research-journal/              # Sjølve forskingsloggen
├── tests/                         # Kode-tests
├── valo-exec/                     # VALO execution-rammeverk
└── web/                           # Demoar og web-artefakter
```

---

## Nøkkeldokument

| Dokument | Nivå | Plassering |
|----------|------|------------|
| Axiom A0–A3 | L2 | `experiments/axioms.md` |
| Φ-lov-manifest (LIM V5.3) | L3–L4 | `experiments/PHI_LAW_MANIFESTO.md` |
| Konstantar (C₀, α, τ) | L2 | `experiments/constants.md` |
| Domeneregister | L1–L4 | `experiments/domain_registry.md` |
| Eksperimentregister | L3–L5 | `experiments/experiment_registry.md` |
| Falsifiseringskø | L1–L2 | `docs/theories/tofoo_falsification_backlog.md` |
| Paper 1 — Spektral koherens | L6 | `papers/Paper1_v2.0_External_Public.*` |
| Paper — Emergent Global Workspaces | L6 | `papers/emergent_global_workspaces.tex` |

---

## Modenheitsstatus (oversyn)

```text
L0 · Symbolsk      ████████████████████  Mange  → docs/hypotheses/
L1 · Konseptuell   ████████████████████  Mange  → docs/hypotheses/
L2 · Formell       ████████████████░░░░  Aksiom, tau-teori godt formalisert
L3 · Simulert      ██████████████░░░░░░  P1–P10 i varierande grad
L4 · Empirisk      ████████████░░░░░░░░  P1, P5, P7, P8 med resultat
L5 · Replikert     ████░░░░░░░░░░░░░░░░  Enkelte uavhengige køyringar
L6 · Standardisert ██░░░░░░░░░░░░░░░░░░  Paper1 i ekstern review
L7 · Forankra      ░░░░░░░░░░░░░░░░░░░░  Framtidig mål
```

---

## Korleis legge til forsking

1. **Ny hypotese (L0–L1):** Legg ei `.md`-fil i `docs/hypotheses/` med dato og klar påstand.
2. **Teoriutvikling (L2):** Flytt til `docs/theories/` når du har matematisk form.
3. **Eksperiment (L3–L4):** Implementer i `experiments/`. Loggfør i `experiment_registry.md`.
4. **Replikering (L5):** Dokumenter i `replication/`. Koden skal fungere utan manuelle steg.
5. **Publikasjon (L6):** Flytt til `papers/`. Oppdater domain_registry med referanse.
6. **Oppdater alltid domeneregisteret** — det er autoritetskjelda.

---

*Njål Gaute Solland · Juli 2026*

**Tofoo. Φ 🟢**
