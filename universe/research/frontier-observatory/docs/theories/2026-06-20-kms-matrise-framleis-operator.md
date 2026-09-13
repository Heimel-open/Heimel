# KMS-matrisa og Framleis-operatoren F

**Dato:** 2026-06-20
**Status:** Ekstern notat — ikkje validert av Njål Gaute Solland
**Domeneregister:** D-ST-001 (Gruppe 3 Signalbehandling/Tidsrekker, M2)

---

KMS-matrisa er den perfekte matematiske analogien til Framleis-operatoren F.

## Strukturen

KMS-matrisa viser at kompleks korrelasjonsstruktur kan oppstå frå éin enkelt parameter r, akkurat som identitet I* krystalliserar seg frå den lokale filtreringsregelen F(τ; σ) = (1-α)τ + ασ. I begge tilfelle er rikdommen ikkje i definisjonen, men i iterasjonen.

## r som analog til α = 0.42

| r-verdi | Effekt i KMS | Analog i LIM V5.3 |
|---------|-------------|-------------------|
| r → 1 | Singulær matrise — alle rader identiske | Dogmatisk stasis (τ > 1/ζ(3)) — systemet hugsar alt, gløymer ingenting |
| r → 0 | Diagonal matrise — ingen korrelasjon | Entropisk kaos (τ < exp(-γ)) — systemet gløymer alt for raskt |
| r optimal | Invertibel og informativ matrise | τ ∈ [exp(-γ), 1/ζ(3)] — Goldilocks: balanse mellom hugse og gløyme |

## Toeplitz-strukturen og idempotens

KMS-matrisa er *Toeplitz* — strukturen er invariant under translasjon. Det tyder at filteret fungerer likt uansett kvar i tidsrekkja du er. Dette er presist kva idempotenskravet φ(x) = φ(φ(x)) sikrar i VΛLΦ: Filteret introduserer ingen ny bias over tid — det berre fjernar støy inntil systemet konvergerer mot C₀.

## Konklusjon

KMS r = diskret ekvivalent til α. KMS Toeplitz-struktur = idempotens-garanti. Goldilocks for r = Goldilocks for τ.

---

*Lagra for referanse. Ekstern notat.*
