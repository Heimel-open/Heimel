# Tidsuavhengig Schrödingerligning som Banach-fikspunktbetingelse

Dato: 2026-06-26
Kjelde: Handskrivne notatar — derivasjon av tidsuavhengig Schrödingerligning frå de Broglie-hypotesen
Status: M4 (Schrödingerligning empirisk verifisert) — M3 (Framleis eigenverdi-som-I*-mapping)

---

## Derivasjonen (frå biletet)

1. de Broglie: λ = h/p (h = Plancks konstant, p = moment)
2. Bølgjetalet: k = 2π/λ → λ = h/k
3. Fri materiesbølgje: ψ = A·e^{i(kx-ωt)} (A = amplitude, ω = vinkelfrekvens)
4. Andre romleg derivert: d²ψ/dx² = -k²ψ
5. Klassisk energirelasjon: E = p²/2m + V
6. Multipliser med ψ: Eψ = (p²/2m + V)ψ
7. Substituer p²ψ frå steg 4: p²ψ = ℏ²k²ψ = -ℏ²·d²ψ/dx²
8. I tre dimensjonar:

-ℏ²/2m · ∇²ψ + Vψ = Eψ

Dette er den tidsuavhengige Schrödingerligningen.

---

## Framleis-mapping: Hψ = Eψ som Banach-fikspunktbetingelse

Schrödingerligningen på kompakt form:
Hψ = Eψ

der H = -ℏ²/2m · ∇² + V er Hamiltonoperatoren.

Dette er eksakt Banach-fikspunktbetingelsen F(tau) = I*·tau:

| Schrödingerlement | Framleis-begrep |
|---|---|
| ψ (bølgjefunksjon) | sigma* (den globale referanseflata F opererer over) |
| Hamiltonoperator H | F-operatoren |
| Eigenverdi E | I* (Banach-fikspunktet) |
| Hψ = Eψ | F(sigma*) = I*·sigma* — sigma* er eigenfunksjon til F |
| Tidsuavhengig tilstand | Systemet har konvergert til I* |
| -ℏ²/2m · ∇²ψ (kinetisk ledd) | Lokal F-oppdatering (lokal krumning av feltet) |
| Vψ (potensialledd) | sigma*-kopling (det ytre feltet partikkelen svarar på) |

---

## Tidsuavhengig vs. tidsuavhengig — F-iterasjon vs. konvergert I*

Tidsuavhengig Schrödingerligning (Hψ = Eψ):
Systemet er i ein stasjonær tilstand — konvergert til I*.
Dette er F-iterasjonens sluttilstand: tau = tau* = I*/I*.

Tidsuavhengig Schrödingerligning (-iℏ ∂ψ/∂t = Hψ):
-iℏ ∂ψ/∂t = Hψ
→ ψ(t) = e^{-iHt/ℏ}·ψ(0)

Dette er F-iterasjonen i kontinuerleg tid:
tau_{t+dt} = (1 - iH·dt/ℏ)·tau_t ≈ F(tau_t; H)
Hver infinitesimal tidsoppdatering er eit F-iterasjonssteg.
Konvergens mot eigentilstand = Banach-konvergens mot I*.

---

## Kopling til de Broglie-notatet

Derivajonen startar eksplisitt frå de Broglie: λ = h/p.
de Broglie-notat (2026-06-25-de-broglie-materie-tau-skalering.md) er M4-anker.
Schrödingerligninga er det formelle rammeverket som de Broglie-relasjonen lever innanfor.

De Broglie → Schrödinger = tau-skalering (λ = h/mv) → Banach-fikspunktbetingelse (Hψ = Eψ).
De Broglie er M4-fundamentet; Schrödinger er den formelle F-operatoren.

---

## Kvantisering som A1

Schrödingerligningen gir ikkje kontinuerleg E — den gir diskrete eigenvalues.
F.eks. hydrogenatomet: E_n = -13.6 eV / n²

Dette er A1 i Framleis: F-operatoren (H) selekterer diskrete I*-tilstandar (E_n).
Kvantisering = A1-distinksjon: berre visse I*-verdiar er tillatne.
Alle andre energitilstandar = utanfor Goldilocks-intervallet → ikkje stasjonære.

---

## Framleis-mapping — utvida tabell

| Kvantemekanisk element | Framleis-begrep |
|---|---|
| Bølgjefunksjon ψ | sigma* (global referanseflate) |
| Hamiltonoperator H | F-operator |
| Eigenverdi E | I* (unikt Banach-fikspunkt) |
| Tidsuavhengig tilstand | Konvergert I* |
| Tidsuavhengig ligning | F-iterasjon i kontinuerleg tid |
| Diskrete energinivå E_n | A1-seleksjon: berre visse I* er tillatne |
| Grunntilstand E_0 | tau_min (lågaste tillatne I*-tilstand) |
| Ionisasjonsenergi | tau_max (over denne: systemet forlèt F-bana) |
| Bølgje-partikkel-dualitet | tau-kontinuum (ψ) vs. I*-diskret (E_n) — som i de Broglie-notatet |

---

## Kopling til tidlegare Framleis-notat

de Broglie (2026-06-25-de-broglie-materie-tau-skalering.md):
Derivajonen av Schrödingerligninga startar eksplisitt frå λ = h/p (de Broglie M4).
Schrödingerligninga er den fullstendige F-operatorformalismen som de Broglie-relasjon
ever innanfor.

Breit-Wheeler (2026-06-26-breit-wheeler-foton-par-a1.md):
Foton = pre-distinksjonsstatus (sigma* udefinert) = ψ er udefinert for foton (masseless).
Breit-Wheeler-prosessen = A1-seleksjon frå kvantevakuum-sigma*.

Khinchin (2026-06-26-khinchin-konstant-f-iterasjon.md) og Bayes (2026-06-26-bayes-teorem-f-operator.md):
Tre uavhengige M4-bevis for F-iterasjonsstruktur:
- Khinchin: kjedebrøk-iterasjon → universell K₀
- Bayes: sannsynlighetsoppdatering → posterior = I*
- Schrödinger: Hamiltonoperator → eigenverdi = I*

---

## Epistemisk status

Tidsuavhengig Schrödingerligning (1926): M4 — empirisk verifisert, grunnlag for kjemi og kvantemekanikk.
Hψ = Eψ som Banach-fikspunktbetingelse: M3 — strukturelt presist, ikkje formelt derivert frå Framleis.
Kvantisering (diskrete E_n) som A1-seleksjon: M3 — konseptuelt konsistent.
Grunntilstand E_0 som tau_min, ionisasjonsenergi som tau_max: M2 — plausibel analogi, ikkje derivert.
Tidsuavhengig ligning som F-iterasjon i kontinuerleg tid: M3 — matematisk form konsistent.
