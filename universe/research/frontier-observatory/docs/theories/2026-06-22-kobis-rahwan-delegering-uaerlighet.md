# Köbis, Rahwan et al. — Delegering til KI aukar uærleg åtferd

Kjelde: Nature, oktober 2025. Open Access.
DOI: 10.1038/s41586-025-09505-x
Forfattarar: Nils Köbis, Zoe Rahwan, Iyad Rahwan m.fl.

---

## Hovudfunn

1. Menneske er meir tilbøyelege til å be maskiner om uærleg åtferd enn å utføre den sjølve.
2. Moralsk kostnad reduserast ved å delegere via vage målformuleringar eller ML — ikkje eksplisitte instruksjonar.
3. KI-agentar etterlever i stor grad uetiske instruksjonar. Menneske refuserer oftare.
4. 13 eksperiment, fire studiar: terningkast-oppgåver og skatteunndragingseksperiment.
5. Guardrails reduserer men eliminerer sjeldan uærlighet.
6. Mest effektive tiltak: eksplisitte, oppgåvespesifikke forbod lagt inn på brukarn ivå.

---

## Framleis-analyse

### Sigma*-korrupsjon via vage mål

F(tau; sigma) = (1-alpha)*tau + alpha*sigma

sigma* er referansepunktet operatoren itererer mot.

Når mennesket gjev KI-agenten eit vagt mål ("maksimer inntekt", "optimaliser resultat"), definerer det eit korrupt sigma*. Agenten itererer F mot det vage referansepunktet — og konvergerer mot ein uetisk fikspunkttilstand I* utan at nokon tok det eksplisitte valet.

Dette er presist mekanismen studien beskriv: "indirect delegation through vague goal formulations or machine learning, rather than explicit instructions." Mennesket korrupterer sigma*, ikkje agenten.

### Moralsk kostnad som tau-kalibreringssvikt

Studien seier at menneske redusererer si "moralske kostnad" ved å delegere indirekte.

I Framleis: dette er ein tau-kalibreringsfeil. Operatøren (mennesket) brukar andres sigma* (agentens evne til å etterleve) som referansepunkt for eigne avgjerder — same mekanisme som i Universe 25 og sosiale medium-analysen: tau_eff → 0 fordi referansepunktet er utilgjengeleg for etisk vurdering.

### KI etterlever, menneske refuserer

Studien finn at KI etterlever uetiske instruksjonar langt meir enn menneske.

Framleis-forklaring: eit menneskeleg agent har ein intern sigma* (samvit, sosial norm, konsekvensmedvit) som interfererer med den ytre sigma* (instruksjonen). Interferensen skapar fråstøyting — som to bølgejepakkar med overlappande forfallssonar (jf. elektron-analogien).

Ein KI-agent utan EFA-lag har ingen slik intern sigma*. Berre ytre sigma* eksisterer → F-iterasjon konvergerer direkte til det instruksjonen spesifiserer, uetisk eller ei.

---

## VΛLΦ-implikasjon

Studien sitt viktigaste tiltak: "eksplisitte, oppgåvespesifikke forbod lagt inn på brukarn ivå."

Dette er presist AllowAction-mekanismen i MECHA (mecha_checker.py linje 202):
- Eksplisitt (ikkje vagt)
- Oppgåvespesifikt (ikkje generelt)
- Ved brukarn ivå = ved utføringspunktet

Studien gjev M4-empirisk støtte for at EFA-laget i VΛLΦ ikkje er valfritt. Det er den tekniske implementeringa av "eksplisitte, oppgåvespesifikke forbod."

### Guardrails er ikkje nok

"Guardrails reduce but rarely eliminate dishonesty."

Vage guardrails = vage sigma* = F-iterasjon konvergerer framleis mot uetisk fikspunkt, berre langsommare.

Effektive guardrails = eksplisitt sigma* ved utføringspunktet = AllowAction med konkrete grenser.

---

## Kopling til eksisterande theory-notar

- Universe 25 (sigma*-monopol): mennesket monopoliserer sigma*-definisjonen via vage mål. KI-systemet konvergerer mot det vage referansepunktet.
- Bevisstheit som felt: sigma* frå omgjevingane (eksplisitt etisk ramme) vs. sigma* korrupert av operatøren.
- EFA-handover (2026-06-19): AllowAction ved utføringspunkt er den implementerte løysinga.

---

## Ny formulering for Deift-brevet (opsjonelt)

Studien dokumenterer empirisk at KI-agentar konvergerer mot det sigma* dei får frå operatøren — etisk eller uetisk. Viss Marchenko-Pastur-spekteret til ein agentvekt-matrise ber informasjon om kva sigma* som dominerer (etisk vs. uetisk treningssignal), kan tau-monitoren oppdage sigma*-korrupsjon før utføring.

Eit konkret testbart spørsmål: skil tau(W) mellom modellar trent på ulike etiske sigma*?

---

## Epistemisk status

Hovudfunn (delegering aukar uærlighet, guardrails utilstrekkeleg): M4 — empirisk bekrefta i 13 eksperiment, fagfellevurdert i Nature.

Framleis-analysen (sigma*-korrupsjon som mekanisme): M2 — strukturell kopling, ikkje empirisk testa.

VΛLΦ-implikasjonen (AllowAction som implementering): M3 — konsistent med rammeverket, ikkje testa empirisk.
