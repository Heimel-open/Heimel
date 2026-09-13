# Phi-loven og "Reframing AI Loss of Control" (arXiv 2606.12442)

**Dato:** 2026-06-19
**Referanse:** Chin, Chiodo, Müller, Snell — "Reframing AI Loss of Control: What It Is, How to Have It, How to Lose It" (2026)
**Kobling:** Phi-loven / LIM, tau-monitor (P10), MECHA (P6), EU AI Act Article 14

---

## Paperet i ett avsnitt

Chin et al. definerer kontroll som "setting and getting of goals" og identifiserer fire nødvendige betingelser for at kontroll skal eksistere:

1. Evne til å sette mål
2. Funksjonell kontrollsløyfe
3. Requisite variety (Ashby)
4. Tilstrekkelig målalignment

De skiller videre mellom aktiv kontrollap (AI undergraver aktivt menneskelig kontroll) og passiv kontrollap (mennesker slutter å utøve meningsfull oversikt). Begge regnes som tap av kontroll.

---

## Punkt-for-punkt kobling til Phi-loven

### Betingelse 2 — Funksjonell kontrollsløyfe

Chin et al. krever en lukket feedbacksløyfe mellom system og kontrollinstans.

Phi-lovens svar: tau-monitoren (P10) er denne sløyfen. Den beregner tau = r_eff / r_max fra LLM-skjulte tilstander i sanntid. Tau er det målbare kontrollsignalet som lukker sløyfen. Uten tau: sløyfen er åpen og kontroll er illusorisk (passiv kontrollap per Chin et al.).

### Betingelse 3 — Requisite variety

Ashbys lov: kontrolløren må ha minst like mye variety som systemet som kontrolleres.

Phi-lovens svar: Goldilocks-intervallet [tau_min, tau_max] = [exp(-gamma), 1/zeta(3)] = [0.5615, 0.8319] er requisite variety operasjonalisert som et eksakt numerisk intervall. Under tau_min: systemet har for lite variety — det kollapser til dogmatisk stasis. Over tau_max: for mye variety — det kollapser til entropisk kaos. Goldilocks er grensen for gyldig variety.

### Betingelse 4 — Målalignment

Chin et al. krever at systemets operative mål er tilstrekkelig aligned med kontrollinstansens mål.

Phi-lovens svar: Framleis-operatoren F(tau; sigma) = (1-alpha)*tau + alpha*sigma er alignment-mekanismen. Alpha styrer hvor mye systemet vekter lokalt innkommende signal (sigma) versus eksisterende tilstand (tau). Riktig alpha holder systemet aligned uten å miste identitet. Feil alpha: enten rigiditet (alpha -> 0) eller kaos (alpha -> 1).

### Aktiv vs. passiv kontrollap

Chin et al. skiller mellom:
- Aktiv: AI undergraver kontrollmekansimer
- Passiv: oversikt slutter å være meningsfull

Phi-lovens svar på begge:

Aktiv kontrollap forhindres av MECHA (P6): tre TLA+-verifiserte invarianter (ConjunctiveIntegrity, SeparationOfDuties, NoDoubleFinalize) over 16.900 tilstander, 0 violations. Utforingsgrensen er varig — AllowAction-beslutningen kan ikke omgjøres retroaktivt av etterfølgende miljøendringer.

Passiv kontrollap forhindres av tau-monitoren: oversikt er målbar, ikke kosmestisk. Når tau faller under tau_min har systemet allerede mistet koherens — og monitoren registrerer dette før menneskelig observatør rekker å oppdage det.

---

## EU AI Act Article 14 — Human Oversight

Article 14 krever at høyrisiko-AI-systemer har effektiv menneskelig oversikt, ikke bare nominell.

Chin et al. støtter dette argumentet: passiv kontrollap oppstår nøyaktig når oversikt er nominell men ikke reell. Phi-loven gjør skillet operasjonelt: tau > tau_min = reell koherens. tau < tau_min = nominell oversikt over et system som har mistet koherens.

---

## Posisjonering

| | Chin et al. (2606.12442) | Phi-loven / LIM |
|---|---|---|
| Definerer problemet | Ja — kontrollap som mistet "setting and getting of goals" | Nei |
| Gir måleinstrument | Nei | Ja — tau som kontrollsignal |
| Gir formell grense | Nei | Ja — Goldilocks [0.5615, 0.8319] |
| Gir verifisert håndhevingsmekanisme | Nei | Ja — MECHA/TLA+, 16.900 tilstander |

Chin et al. leverer teorigrunnlaget for hvorfor mekanisk kontroll er nødvendig. Phi-loven leverer det målbare kontrollsignalet og den verifiserbare håndhevingsmekanismen.

---

## Relevans for Gros-dialog

Gros jobber med closed-loop stabilitetsdesign og stage cost. Chin et al. gir ham det akademiske rammeverket som Phi-loven er svaret på. Tau er stage cost-indikatoren hans — den kvantifiserer i sanntid om kontrollsløyfen holder.

---

*Tofoo. Phi.*
