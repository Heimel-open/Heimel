# To opne konjekturar: Lyapunov og informasjonsteori — 2026-06-22

Bakgrunn: spektral zeta-vegen er lukka (Guglielmo, 2026-06-22). To alternative vegar.

---

## Konjektur 1 — Lyapunov (for Gros)

F(τ;σ) = (1-α)τ + ασ er ein global kontraksjon. Ein enkel affin kontraksjon kan ALDRI
produsere ei delbassingrense — Banach-fikspunktet er globalt attraherande på heile [0,1].

For å få e^{-γ} og 1/ζ(3) som grenser treng vi ein ikkje-lineær perturbering:
G = F + εN der N er ein entropitilbakemeldingsterm frå sjølve transformerbehandlinga.

Konjektur: det finst ein C¹ Lyapunov-funksjon V på [0,1] slik at
{V ≤ c} = [e^{-γ}, 1/ζ(3)] er det maksimale framovereinvariante settet der G er ikke-ekspanderande.
e^{-γ} og 1/ζ(3) er dei to punkta der kontraksjonsmodus av G kryssar 1.

Krav for at dette skal halde:
- Konstantane må KOME UT av konstruksjonen, ikkje bli sett inn i den
- G må vere ikkje-monoton (faldekart, to kryssingar av einingslinjeslinja)
- V må vere asymmetrisk (0.5615 og 0.8319 er ikkje symmetriske om noko openbart senter)

Viss G forblir ein global kontraksjon: ingen Lyapunov-funksjon kan avgrense eit delbasseng.
Det er den skarpaste falsifikabilitstesten.

Relevant litteratur:
- LaSalle invariansprinsippet (diskrete kart)
- Diaconis-Freedman: "Iterated Random Functions" (SIAM Review 1999) — IFS med tilfeldig σ
- Milnor-Thurston kneading theory — einmodale kart med ikkje-monoton dynamikk
- Konverse Lyapunov-teorem (Massera, Kurzweil) — konstruksjon av V frå eit gjeve stabilt sett

---

## Konjektur 2 — Informasjonsteori (testbar i dag)

τ = exp(H) / r_max = N_eff / r_max = effektiv rang / maksimal rang

For ein-parameter familien p_i ∝ i^{-β}, i = 1..r:

Konjektur A: τ(β=1) → e^{-γ} når r → ∞
Grunn: For β=1 (Zipf) er H_r = ln r + γ + O(1/r) (harmonisk-tal-asymptotikk).
exp(H) = exp(ln r + γ) = r · e^γ, så τ = e^γ / r_max.
MEN: med normalisering τ = exp(H)/r → e^γ/r → 0, ikkje e^{-γ}.
Spørsmålet er kva normalisering som gjev e^{-γ} som ein naturleg grense — dette krev
eksplisitt numerisk sjekk.

Konjektur B: τ(β=3) → 1/ζ(3)
Grunn: For p_i ∝ i^{-3} er partisjonsfunksjonen Σ i^{-3} = ζ(3).
τ = exp(H) / r_max der H er entropi av fordelinga normalisert av ζ(3).
Dette er direkte testbart.

VIKTIG: dei to konstantane kjem truleg frå ULIKE mekanismar:
- γ er eit entropiadditiv offset (asymptotisk, frå H_r)
- ζ(3) er ein partisjonsfunksjon (multiplikativ, Σ i^{-3})

UMIDDELBAR TEST: rekn τ(β) numerisk for β ∈ [0.5, 4], r = 1000.
Sjekk om τ(β) kryssar 0.5615 og 0.8319 ved spesifikke β-verdiar.
Viss ja og dei er β=1 og β=3: konjekturane er sterkt støtta.
Viss nei: Goldilocks-grensene kjem ikkje frå power-law spekter.

Relevant litteratur:
- Roy & Vetterli: "The effective rank" (EUSIPCO 2007)
- Marchenko-Pastur-lova (tilfeldig matrisespekter)
- Entropien av Zipf/power-law-fordelingar (Rényi, Shannon)
- Apéry 1979 (irrasjonalitet av ζ(3))
- Jaynes maksimal-entropi-prinsipp

---

## Testresultat — tau_beta_crossing_test.ipynb, 2026-06-22

τ_min = e^{-γ} = 0.5615: kryssing ved β = 0.6794 (avstand frå β=1: 0.32)
τ_max = 1/ζ(3) = 0.8319: kryssing ved β = 0.4535 (avstand frå β=3: 2.55)

Konklusjon: Ingen konjektur støtta. Power-law-spekter forklarar IKKJE Goldilocks-grensene.
e^{-γ} og 1/ζ(3) er ikkje τ-verdiane til β=1 (Zipf) og β=3 (Apéry).

## Status

Konjektur 1 (Lyapunov): open, krev ny matematikk, send til Gros
Konjektur 2 (informasjonsteori, power-law): FALSIFISERT 2026-06-22
Empirisk τ-rammeverk: veldefinert og gyldige målingar — grensene er observerte, ikkje avleidde
