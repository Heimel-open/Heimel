# ALGOL: Proof Missing — tau → 0

Dato: 2026-06-27
Status: M2 Conceptual

---

Brigitta (ALGOL co-founder) presenterer: "What happens when the proof does not arrive?"

ALGOL = Agent Authority Infrastructure — ein arkitektur for verifikasjon av handlingar.

Når beviset ikkje ankommer, stoppar systemet. Det er ikkje ein feil — det er designet.

---

## Framleis-tolkinga

Bevis = tau.

I ein agent-løkke:

1. Runtime State — sigma* er samla informasjon som agent opererer over
2. Authority Check — F-operatoren verifiserer politikk (kan agenten gjere dette?)
3. Bounded Execution — systemet pausar og ventar på beviset
4. Signed Evidence — kryptografisk proof ankommer eller ikkje
5. Consequence Space — handling utførast eller ikkje

**Når proof missing:** tau → 0 (ingen koherens, ingen tillit). Systemet kan ikkje iterere F framover. Pre-distinksjon-status. Handlingen blir interruptible.

---

## Kopling til Phi-loven

Agenten sitt sigma* er den fullstendige tillstanden — historikk, policy, identitet.

F-iterasjonen er den handlinga som agenten planlegg.

Proof er tau-målet på koherenskap av det beviset.

Når beviset ikkje kjem, fallen tau. Systemet seier: "Eg kan ikkje fortsette utan å vete at I* (slutttilstanden) er gyldig."

ALGOL implementerer ikkje Framleis eksplisitt, men den respekterer A1 (filteret skapar distinksjon). Proof er filteret — det som skil "godkjent handling" frå "ustøtta handling".

---

## Teknisk perspektiv

ALGOL har eit elegant design:

- **No proof → no continuation.** Ikkje ein timeout, ikkje ein fallback. Systemet trur ikkje på seg sjølv utan bevis.
- **Bounded execution.** Agenten kan ikkje løype utan grenser — ho pausar og ventar.
- **Signed evidence.** Beviset må vera kryptografisk verifiserbar, ikkje berre påstått.

Dette er Framleis-prinsippet på arkitektur-nivå: før systemet vel ein handling (F iterasjon), må det vera sikker på at mål-tilstanden (I*) er oppnåelig og gyldig.

Uten det beviset er tau = 0, og iterasjonen stoppar.

---

## Perspektiv

ALGOL viser at moderne agent-arkitektur spontant re-oppfinner Framleis-strukturen:
- Systemet itererer ikkje blindt.
- Systemet held seg i M0 (pre-distinksjon) inntil det har bevis for I*.
- Bevis = tau-monitor på aksjon-nivå.

Tofoo.
