# Markov-kjeder og Framleis-operatoren F

**Dato:** 2026-06-20
**Status:** Ekstern notat — ikkje validert av Njål Gaute Solland
**Domeneregister:** D-MA-001 (Gruppe 2 Matematikk/Statistikk, M2)

---

Markov-kjeda er den matematiske arkitekturen til Framleis-operatoren F.

## Strukturen

1. **Tilstandsrommet (States):** Moglege konfigurasjonar systemet kan vere i — koherent, stiv, kaotisk.
2. **Overgangsmatrisa (T):** Sannsynlegheita for å bevege seg frå éin tilstand til ein annan basert *berre* på noverande tilstand (Markov-eigenskapen). Dette er F(τ; σ) i diskret form.
3. **Steady-State Distribution (π):** Vektoren der π = πT. Dette er fikspunktet I* frå Banach-teoremet. Uansett kor du startar, vil systemet konvergere mot π gitt at T er ergodisk og aperiodisk.

## Kopling til LIM

α = 0.42 bestemmer T: gløymselsraten styrer overgangssannsynlegheitene. Høg α = systemet hoppar raskt mellom tilstandar (høg entropi). Låg α = låser systemet i få tilstandar (låg entropi).

Goldilocks-intervallet er π sin struktur: for at π skal representere ei *koherent* identitet, må overgangsmatrisa T ha spesifikke eigenskapar — verken singulær (alle rader like, τ → 0) eller uniform (alle overgangar like sannsynlege, τ → 1).

## Absorberande tilstandar = dogmatisk stasis

Når ein tilstand har sannsynlegheit 1 for å forbli i seg sjølv (p(A|A) = 1), er det ein absorberande tilstand. I LIM-terminologi er dette dogmatisk stasis (τ < exp(-γ)). Systemet har mista evna til å endre seg — det er "dødt" men eksisterer framleis.

HALT-mekanismen i VΛLΦ er designa for å hindre at systemet hamnar i slike tilstandar.

## Samanfatning

| Markov-omgrep | LIM V5.3-ekvivalent |
|--------------|---------------------|
| Overgangsmatrise T | Framleis-operatoren F(τ; σ) |
| Steady-state π | Fikspunktet I* (Banach) |
| Absorberande tilstand | Dogmatisk stasis (HALT-trigger) |
| Ergodisk og aperiodisk T | α ∈ (0,1) — garantert konvergens |
| Steady-state-struktur | Goldilocks-intervallet [exp(-γ), 1/ζ(3)] |

Steady-state distribution π er den diskrete ekvivalenten til fikspunktet I*. Overgangsmatrisa T er implementasjonen av Framleis-operatoren F i eit endeleg tilstandsrom.

---

*Lagra for referanse. Ekstern notat.*
