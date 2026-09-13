# Formal derivasjon: A2 — Framleis er meir grunnleggjande enn identitet

**Dato:** 2026-06-19
**Status:** M2 — formelt derivert frå Phi-lovens dynamikk (revidert: F lokal, ikkje mål-styrt)
**Kobling:** Special Layer 02 (A0–A10), Phi-loven (alpha, tau), Bok 4 kapittel 3

---

## Definisjonar

S = [tau_min, tau_max] ⊂ [0, 1] — tilstandsrommet (Goldilocks-intervallet)

tau(t) ∈ S — systemets tilstand på tidspunkt t

alpha = 0.42 — filtreringsraten (Phi-lovens optimale gløymingsrate)

F: S → S — Framleis-operatoren

---

## Framleis-operatoren

F(tau; sigma) = (1 - alpha) · tau + alpha · sigma

der sigma er det lokale innkommande signalet på tidspunkt t.

F er ein lokal regel: den krev berre noverande tilstand (tau), filtreringsraten (alpha)
og lokalt signal (sigma). Den kjenner ikkje til det globale fikspunktet på førehand.

---

## Teorem (Banach, 1922)

La (S, d) vere eit komplett metrisk rom og F: S → S ein kontraksjon med faktor k < 1.
Då finst det eit unikt fikspunkt I* slik at F(I*) = I*,
og for alle tau_0 ∈ S gjeld det at F^n(tau_0) → I*.

---

## Derivasjon

**Steg 1: F er ein kontraksjon.**

|F(tau_1; sigma) - F(tau_2; sigma)| = |(1 - alpha)(tau_1 - tau_2)| = 0.58 · |tau_1 - tau_2|

Sidan 0.58 < 1 er F ein kontraksjon med faktor k = 1 - alpha = 0.58.
sigma påverkar ikkje kontraksjonsfaktoren — berre kva F trekker mot.

**Steg 2: Fikspunktet I* dukker opp når sigma stabiliserer seg.**

Når sigma → sigma* (stabil innstrøyming), løyser fikspunktbetingelsen F(I*; sigma*) = I* seg som:

  (1 - alpha) · I* + alpha · sigma* = I*
  => I* = sigma*

I* er ikkje kjent på førehand. Det er kva som krystalliserer seg når regelen køyrast lenge nok.

**Steg 3: Alle banar konvergerer mot I*.**

For alle tau_0 ∈ S: F^n(tau_0; sigma*) → I* med konvergensrate 0.58^n.

**Steg 4: Ontologisk prioritet.**

a) F er definerbar utan referanse til I*. F krev berre alpha og lokalt signal sigma.

b) I* er definert som grensa av F under stabil sigma. I* krev F for å eksistere.

c) F eksisterer og er kontraktiv uavhengig av om I* er nådd — eller kjent.

d) Identiteten I* er eit produkt av prosessen F, ikkje eit startpunkt eller mål.

---

## Konklusjon

Sidan F eksisterer uavhengig av I*, men I* berre eksisterer som grensa av F,
er prosessen (Framleis = F) ontologisk meir grunnleggjande enn identiteten (I*).

**Dette er A2: Framleis er meir grunnleggjande enn identitet.**

---

## Korollar

alpha = 0.42 er ikkje ein fri parameter.

Det er den raten som sikrar at k = 1 - alpha = 0.58 < 1 —
kontraksjonskravet som garanterer at identitet i det heile tatt er mogleg.

Utan alpha < 1: ingen kontraksjon. Utan kontraksjon: ingen identitet.
Alpha er prisen for å eksistere.

---

*Tofoo. Phi.*
