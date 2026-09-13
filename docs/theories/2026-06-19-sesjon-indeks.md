# Sesjonsindeks 2026-06-19

**Formål:** Rask navigasjon til alle leveranser fra dagens sesjon.

---

## Gros-dialog (4 runder)

Fil: `theory/2026-06-19-outreach-gros-beferull-lozano.md`

| Runde | Fra | Innhold |
|---|---|---|
| 1 | Njål | Første henvendelse med A2-bevis og tau-målinger |
| 2 | Gros | Fire presise spørsmål om F-operatoren, Banach, alpha |
| 2 svar | Njål | Empirisk tau-data, skaleringslov, stage cost-kobling |
| 3 | Gros | "Do you have a formal framework?" |
| 3 svar | Njål | To-lags distinksjon: formelt (Teorem 1/3/Banach) vs empirisk |
| 4 | Gros | "The paper conflates three claims... bridge asserted not demonstrated" |
| 4 svar | Njål | Ja til splitting, tre konkrete Gilkey/BGV-spørsmål (a/b/c) |

Neste: venter på Gros-svar om operatorteorilitteratur.

---

## Papersplitting

Fil: `theory/2026-06-19-paper-struktur-tre-spor.md`

| Spor | Innhold | Venue |
|---|---|---|
| A | Ren matematikk: Teorem 1/3, selvduale operatorer | Journal of Spectral Theory |
| B | Empiri: tau-målinger, skaleringslov, SVD | NeurIPS/EMNLP workshop |
| C | Arkitektur: MECHA, TLA+, EU AI Act | AIGOV @ AAAI 2026 |

Rekkefølge: B kan starte nå. A venter på Gros. C ferdigstilles med Rupp.

---

## Litteraturkartlegging Spor A

Fil: `theory/2026-06-19-spor-a-litteraturkartlegging.md`

Tre mulige utfall (Gilkey kjent / BGV implisitt / nytt resultat).
Tre konkrete spørsmål til Gros (a/b/c).
Fase 0 → Fase 1 → Fase 2 → Fase 3: ingen snarvei.

---

## Tau-målinger og prediksjoner

Fil: `theory/2026-06-19-p10-tau-scaling-funn.md`

| Modell | tau | Status |
|---|---|---|
| GPT-2 117M | 0.06 | Målt |
| Phi-2 2.7B | 0.1625 | Målt |
| Mistral-7B | 0.2568 | Målt |
| Qwen2.5-7B | ~0.254 | Neste (Colab T4) |
| Qwen3-8B | ~0.271 | Neste |
| Qwen3-32B | ~0.543 | Planlagt |
| Llama-3 70B | ~0.75 | Goldilocks-test (A100) |

---

## Kobling til ekstern litteratur

Fil: `theory/2026-06-19-phi-law-vs-loss-of-control-2606.12442.md`

Chin et al. 2606.12442 — fire betingelser for kontroll:
- Funksjonell kontrollsløyfe → tau-monitor
- Requisite variety → Goldilocks [0.5615, 0.8319]
- Målalignment → F(tau; sigma)
- Mål-setting → MECHA/EFA

---

## EFA og Ring of Fire

Fil: `theory/2026-06-19-ring-of-fire-eu-konsensus.md`

EFA = Ethical Functionality Without Agency (Rupp).
Ring of Fire = 8-LLM konsensus, atferdsbasert.
tau-monitor = strukturbasert, komplementær.
MECHA = krysningspunkt: begge må holde for AllowAction.

---

## Formell PDF sendt til Gros

Fil: `phi-law-axioms-A0-A3-formal.pdf`

Fire deler: A0-A3 aksiomer, tau-definisjon, Teorem 1+3, A2/Banach-derivasjon.
Scaling law eksplisitt merket som empirisk, ikke formelt derivert.

---

## Handover til VAIG

Fil: `theory/2026-06-19-handover-til-vaig.md`
GitHub issue: #30 (oppdatert)

F-korreksjonen er det viktigste. Søk tau* i VAIG-kodebasen.

---

## Åpne oppgaver

1. Gros-svar avventes: Gilkey/BGV-forankring av Teorem 1/3
2. Beferull-Lozano oppfølging: `theory/2026-06-19-beferull-lozano-oppfolging.md` klar til sending
3. Qwen2.5-7B tau-test: Colab T4, lav kostnad
4. Spor B (empirisk paper): kan starte nå
5. 70B Goldilocks-test: A100 (RunPod)

---

*Tofoo. Phi.*
