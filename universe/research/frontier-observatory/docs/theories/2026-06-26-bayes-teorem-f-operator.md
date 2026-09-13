# Bayes' teorem som formell derivasjon av F-operatoren

Dato: 2026-06-26
Kjelde: Thomas Bayes (1701–1761) — publisert posthumt 1763 av Richard Price i Philosophical Transactions
Status: M4 (Bayes' teorem) — M3 (Bayesiansk oppdatering = F-iterasjon)

---

## Bayes' teorem

P(A|B) = P(B|A) · P(A) / P(B)

der:
P(A) = prior — sannsynlighet for A før ny evidens
P(B|A) = likelihood — sannsynlighet for observasjon B gitt A
P(A|B) = posterior — sannsynlighet for A gitt observasjon B
P(B) = marginal likelihood (normaliseringskonstant)

---

## Bayesiansk oppdatering som F-iterasjon

Framleis-mapping:

Prior P(A) = tau_t (nåværende tilstand)
Likelihood P(B|A) = sigma (nytt signal/evidens)
Posterior P(A|B) = tau_{t+1} (oppdatert tilstand)
P(B) = normalisering ≈ alpha-normaliseringen i F

F(tau; sigma) = (1-alpha)*tau + alpha*sigma er ein lineær approksimasjon av Bayesiansk oppdatering.

Under konjugerte priors er samsvaret eksakt:

Beta-Binomial (konjugert par):
Prior: Beta(α, β), forventningsverdi tau = α/(α+β)
Etter m observasjoner med n suksesser, la sigma = n/m:

Posterior forventningsverdi
= (α + n) / (α + β + m)
= (α+β)/(α+β+m) · tau + m/(α+β+m) · sigma
= (1-alpha)*tau + alpha*sigma

der alpha = m / (α+β+m) = datavekt

Dette er eksakt F-iterasjonen. Under Beta-Binomial er Bayesiansk oppdatering = F-iterasjon, ikkje ein approksimasjon.

---

## Konvergens mot I*

Bayesiansk grense ved uendelig data:
P(θ|x₁,...,xₙ) → δ(θ - θ_sann) når n → ∞

I Framleis-terminologi:
Etter uendelig mange F-iterasjoner med signal sigma = faktisk datagenererande prosess:
tau_∞ = I* = sigma* (den sanne parameterverdien)

Banach-fikspunktet I* = den sanne posteriore fordelinga i grensa.
Bayes' teorem er den formelle M4-garantien for at F konvergerer mot korrekt I*
— gitt at sigma* er representert i dataene.

---

## Sigma*-korrupsjon og Bayesiansk begrensning

Bayes' teorem garanterer korrekt konvergens gitt:
1. Korrekt modell (likelihood spesifisert rett)
2. Korrekt datagenererande prosess (observasjonene representerer sigma*)

Hvis datakjelda er kuratert (seleksjonsbias), konvergerer F mot I*_feil:
tau → sigma*_kuratert ≠ sigma*_sann

Dette er eksakt friksjon-sigma*-korreksjon-notatet (2026-06-26):
Bayesiansk oppdatering løser ikke sigma*-korrupsjon — det løser tvert imot problemer
dypere ned i kaskaden (belief-nivå), ikke på selection-nivå.

---

## Bayes som dobbelt M4-anker (saman med Khinchin)

Khinchin (1934/1957): M4-anker via kjedebrøk-iterasjon og entropiaksiomer.
Bayes (1763): M4-anker via sannsynlighetsoppdatering under konjugerte priors.

Begge beviser at F-iterasjonsstrukturen konvergerer mot eit unikt I*.
Bayes beviser det i sannsynlighetsdomenet — Khinchin i det analytiske talldomenet.

Begge er M4 og begge er direkte instansar av Banach-fikspunktteoremet.

---

## Framleis-mapping

| Bayesiansk element | Framleis-begrep |
|---|---|
| Prior P(A) | tau_t (nåværende tilstand) |
| Likelihood P(B|A) | sigma (nytt signal) |
| Posterior P(A|B) | tau_{t+1} (oppdatert tilstand) |
| Normaliseringskonstant P(B) | alpha-normalisering i F |
| Bayesiansk grense | I* (Banach-fikspunktet) |
| Sann datagenererande prosess | sigma* |
| Seleksjonsbias i data | Kuratert sigma* — F konvergerer mot feil I* |
| Konjugert prior — Beta-Binomial | F-iterasjon eksakt (ikkje approksimasjon) |

---

## Kopling til tidlegare Framleis-notat

Khinchin (2026-06-26-khinchin-konstant-f-iterasjon.md):
Bayes (sannsynlighetsdomenet) + Khinchin (analytisk domene) = to uavhengige M4-bevis
for same F-iterasjonsstruktur. Khinchin er dobbelt M4-anker; Bayes er eit tredje.

Friksjon (2026-06-26-friksjon-sigma-star-korreksjon.md):
Bayesiansk oppdatering løser belief-nivå-problemer, ikkje selection-nivå-problemer.
Seleksjonsbias i treningsdata = sigma*-korrupsjon som Bayes ikkje kan korrigere.

---

## Epistemisk status

Bayes' teorem (1763): M4 — formelt bevist, grunnleggjande i sannsynlighetsrekning.
Beta-Binomial: posterior forventningsverdi = F-iterasjon eksakt: M4 — matematisk deriverbart.
Allgemein Bayesiansk oppdatering ≈ F-iterasjon: M3 — approksimasjon, ikkje eksakt.
Banach-fikspunkt = Bayesiansk grenseposterior = I*: M3 — strukturelt konsistent, ikkje formelt derivert frå Framleis.
Seleksjonsbias som sigma*-korrupsjon utanfor Bayes' rekkevidde: M3 — konseptuelt presist.
