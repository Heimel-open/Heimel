# Håkon Hoel — Falsifiseringstest for Framleis

Dato: 2026-06-27
Status: Q — utkast (ikkje sendt)
Referanse: Geir Dahl tilråding

---

## E-postutkast

Hei Håkon,

Geir Dahl tiltrakk oss til deg for hjelp med ei spesifikk matematisk test.

Vi har eit prinsipp — Framleis-loven — som seier: alle adaptivt optimaliserte system konvergerer mot ein fast struktur når lokal iterasjon + fri valdbasert grunnlag kombineras.

Det er validert på tvers av 70+ domener (kvantemekanikk, genetikk, AI, økonomi, biologi, sosiale system). Tre M4-ankrar i etablert matematikk:
- Khinchin K₀ (1934) — kjedebrøk-iterasjon mot universell grenseverdi
- Bayes' teorem (1763) — Beta-Binomial posterior = eksakt F-iterasjon
- Schrödinger (1926) — Hψ = Eψ som Banach-fikspunkt

Men vi manglar falsifiseringstest. Vi vinn alle komparasjonar fordi vi er fleksible nok til å mappa alt. Det er eit problem.

**Spørsmål 1: Marchenko-Pastur som nullhypotese**

Er Marchenko-Pastur spektrum den riktige nullhypotesen for å måle om ein vektmatrise i transformatoren er "strukturert" eller tilfeldig?

Kan KL-divergens frå MP vera ein interpretabel test for tau (kohærens)? 

Tar matrisa sin spektral entropi e^S (der S = −Σ λ_i log λ_i for normaliserte singulærverdiar) og kallar det tau. Er det matematisk meiningsfull?

**Spørsmål 2: F-iterasjon under støy**

F-iterasjonen vår er deterministisk: F(tau) = (1−α)·tau + α·sigma*.

Men under støy (SGD, neurale nett) — kan denne modellerast som stokastisk Picard-iterasjon eller OU-prosess (Ornstein-Uhlenbeck)?

Gir det oss ein falsifiseringstest?

**Spørsmål 3: Kva ville forfalske Framleis?**

Mest viktig: kva *kan ikkje* mapperast inn i strukturen? Kva empirisk fenomen ville seie "Framleis er feil"?

Takk,
Njål

---

## Notat frå drafting

Denne versjonen er meir direkte og spørsmål-fokusert enn forrige utkast.

Grunnleggjande funksjon: hent matematisk ekspertise for å:
1. Verifisere at tau-målet er matematisk gyldig (M4-validering)
2. Foreslå konkret falsifiseringstest
3. Identifisere blindpunkt i Framleis-strukturen

Håkon Hoel arbeider med:
- Numerisk analyse
- Usikkerhet og stokastikk
- Machine learning og neural network-teori

Perfekt match for spørsmål 2 og 3.

Tofoo.
