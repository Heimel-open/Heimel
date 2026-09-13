# Elektron som bølgje: Framleis-operatoren i kontinuerleg form

Dato: 2026-06-22
Kjelde: Fysikk-tekst om bølgedynamikk og elektron-fråstøyting, 2026-06-22

---

## Bølgelikninga som Framleis-operator

Teksten presenterer:

dW/dt = F[W] - div(kappa_c * W)

Der:
- F[W] = det lokale oppdateringsfeltet (framleis-dynamikken)
- div(kappa_c * W) = divergensleddet — utoverstrøyming frå forfall

Framleis-operatoren i diskret form:

F(tau; sigma) = (1-alpha)*tau + alpha*sigma

Samanstilling:

| Bølgjelikningar | Framleis | Rolle |
|---|---|---|
| F[W] | (1-alpha)*tau | Lokal vedlikehald |
| div(kappa_c * W) | alpha*(tau - sigma) | Koplingsterm mot sigma* |
| kappa_c | alpha | Koplingskonstant |
| Stabile stående moder | Goldilocks-sona | Attraktortilstand |
| Balmer-diskretisering | Diskrete tau-nivå | Spektrale moder |

Bølgelikninga er ein kandidat for den kontinuerlege Framleis-operatoren.

---

## Forfalstalet og Goldilocks

Bølgjepakken har ein forstig ∇W < 0 på forfallet.

Momentumstrøym: J = -kappa_c * W * ∇W

Sidan W > 0 og ∇W < 0: J er positiv/utover.

I Framleis-rammeverket:
- Tau under Goldilocks-grensa: forfallet dominerer, stående moder ikkje stabile — tau_min
- Tau i Goldilocks [0.5615, 0.8319]: forstand og forfall i balanse — stabile moder
- Tau over Goldilocks-grensa: fronten dominerer, ingen forfalshale, inga resonans — tau_max

Fråstøyting mellom elektron = to bølgjepakkar der forfallssonene overlapper.
Utoverstrøymingane møter kvarandre og gjer tilnærming umuleg.

Dette er presist kva Goldilocks-sona gjer i tau-rommet: systemet held seg i stabil modestilstand. Kvar gong tau nærmar seg kollapssona, er det forfallet som pressar tilbake — same mekanisme som elektron-fråstøyting.

---

## Balmer-formelen som diskrete tau-nivå

Balmer:

1/lambda = R * (1/4 - 1/n^2)

Stående moder W_n(r) ~ sin(k_n * r), k_n ~ 1/n

gir:

1/lambda ~ (1/n1^2 - 1/n2^2)

I Framleis: tau er spektral entropi av singulærverdi-spekteret. Kvar stabil eigentilstand (stående mode) korresponderer til eit diskret tau-nivå der F-iterasjonen konvergerer.

Balmer er den atomære tau-monitoren: ein empirisk observasjon av kva diskrete moder systemet kan ha.

---

## Skipanalogien (Bernoulli/bølgedynamikk)

To skip side ved side: bølgjene mellom skipa dannar overlappande forfallssonar.
Utoverstrøymingane kolliderer — skipa kan ikkje røre kvarandre.

Same matematikk, anna medium.

I Framleis-språk: to system med overlappande sigma*-felt vil oppleve tau-fråstøyting — konvergens mot same fikspunkt er blokkert av interferens mellom forfallssonene.

---

## Konsekvens for Framleis

Det fins ingen "ladning" i Framleis heller.

tau er eit felt, ikkje ein eigenskap.
F-iterasjonen er bølgedynamikk i diskret tid.
Fråstøyting mellom system = overlappande forfallssonar i tau-rommet.

Dei tre grunnleggjande fenomena frå bølgjeteksten:

| Fenomen | Bølgjedynamikk | Framleis |
|---|---|---|
| Diskrete nivå | Stående moder | Diskrete tau-attraktar |
| Stabilitet | Front/forfall-balanse | Goldilocks-sona |
| Fråstøyting | Forfallssone-kollisjon | Tau-interferens |

---

## Opent spørsmål

Er kappa_c i bølgelikninga identisk med alpha i Framleis?

Viss ja: Framleis-koplingskonstanten alpha = 0.42 burde korrespondere til eit bestemt forfallsmodus i bølgje-substrat.

Er det ein mapping mellom spektral tau (SVD-basert) og bølgjefunksjonsamplituda W der tau = r_eff/r_max svarer til eit normalisert L2-integral av W^2?

Marchenko-Pastur-testen kan kaste lys på dette: MP-fordelinga beskriv nettopp den statistiske strukturen til bølgjefunksjonar i tilfeldig media.

---

## Konklusjon

Bølgelikninga dW/dt = F[W] - div(kappa_c * W) er ein naturleg kandidat for den kontinuerlege analogen til Framleis-operatoren F(tau;sigma).

Elektron-fråstøyting utan ladning = tau-interferens i Goldilocks-rommet.
Balmer-diskretisering = empirisk tau-monitor for atomære system.
Skipanalogien = universaliteten til forfallsdynamikk på tvers av substrat.

Ikkje ladning. Ikkje kraft. Berre bølgeform og forfall.
