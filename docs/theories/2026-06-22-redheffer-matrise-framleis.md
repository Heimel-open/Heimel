# Redheffer-matrisa og Framleis — filter, divisibilitet og Mertens

Dato: 2026-06-22

---

## Kva er Redheffer-matrisa

R_{ij} = 1 viss i=1 eller i|j (i dividerer j), ellers 0.

Første kolonne: alle 1-ar.
Alle andre kolonne j: 1 berre i radene der i|j.

Determinanten:
det(R_n) = M(n) = Σ_{k=1}^n μ(k)

der μ(k) er Möbius-funksjonen:
- μ(1) = 1
- μ(k) = 0 viss k har ein gjentatt primfaktor
- μ(k) = (-1)^r viss k er produkt av r distinkte primtal

---

## Kopling til Riemann-hypotesen

Mertens-funksjonen M(n) = Σ μ(k) er direkte kopla til RH:

Viss M(n) = O(n^{1/2 + ε}) for alle ε > 0, er RH sann.

RH er ekvivalent med at Redheffer-matrisas determinantvekst er sublinear i riktig forstand.

---

## Koplinga til Framleis

### A1: Filteret finst

Redheffer-matrisa er ein bokstaveleg filter:
- R_{ij} = 1 viss i|j (resonans/divisibilitet)
- R_{ij} = 0 ellers

Divisibilitetsstrukturen er filterfunksjonen. Ikkje alle j passerer — berre dei som har i som faktor. Dette er presist A1: "Filteret finst — systemet lagar distinksjon."

### tau av Redheffer-matrisa

Redheffer-matrisa R_n er ein n×n matrise med kjende singulærverdi-eigenskapar.

Opent spørsmål: kva er tau(R_n) = exp(H) / sqrt(n) der H er spektral Shannon-entropi av singulærverdiane til R_n?

Hypotese: tau(R_n) ligg i nærleiken av Goldilocks-sona [e^{-γ}, 1/ζ(3)] = [0.5615, 0.8319], fordi dei same konstantane (γ og ζ(3)) dukkar opp i den analytiske strukturen til M(n).

### ζ(3) og Goldilocks

Den øvre Goldilocks-grensa er 1/ζ(3) = 1/Apéry = 0.8319.

Redheffer-matrisas determinant involverer ζ-funksjonen via Möbius (μ og ζ er kopla via Dirichlet-serien).

Spørsmålet til Percy Deift (om kva E[exp(H)/sqrt(n)] er under MP-fordelinga) kan ha eit meir konkret svar viss vi kan vise at Redheffer-matrisas singulærverdi-spektrum ber det same ζ-fingeravtrykket.

---

## Første kolonne = sigma*

Redheffer-matrisa har alle 1-ar i kolonne 1.
Kolonne 1 = referansevektoren som alle andre kolonnar vert målt mot.

I Framleis: kolonne 1 = sigma* (det konstante referansepunktet).
F(tau; sigma) = (1-alpha)*tau + alpha*sigma — der sigma er "alltid til stades" uavhengig av j.

Dette er den matematiske strukturen til ein Framleis-operator: eitt fast referansepunkt (kolonne 1 = alle 1-ar) pluss ein variabel komponent (divisibilitetsstrukturen).

---

## Konkret testidé

Berekn tau(R_n) for n = 10, 20, 50, 100, 500:

```python
import numpy as np

def redheffer(n):
    R = np.zeros((n, n))
    for i in range(1, n+1):
        for j in range(1, n+1):
            if i == 1 or j % i == 0:
                R[i-1, j-1] = 1
    return R

def tau(M):
    s = np.linalg.svd(M, compute_uv=False)
    p = s**2 / np.sum(s**2)
    p = p[p > 0]
    H = -np.sum(p * np.log(p))
    return np.exp(H) / np.sqrt(M.shape[1])

for n in [10, 20, 50, 100]:
    R = redheffer(n)
    print(f"n={n}: tau={tau(R):.4f}")
```

Predikert: tau(R_n) → noko nær [0.5615, 0.8319] ettersom n aukar, fordi divisibilitetsstrukturen har log-tettleik som skalerer med γ.

---

## Kopling til Percy Deift

Deift arbeider med spektralteori og random matrix theory.
Redheffer-matrisa er ikkje tilfeldig — ho er deterministisk strukturert via primtal.

Men: for store n oppfører singulærverdi-spekteret til R_n seg statistisk, og MP-fordelinga kan vere ein god approksimant.

Spørsmålet til Deift kan omformulerast som:
"For the Redheffer matrix R_n, what is the limiting distribution of its normalized effective rank τ = exp(H)/sqrt(n), and does it involve the constants γ or ζ(3)?"

Dette er eit konkret og matematisk presist spørsmål som Deift faktisk kan ha meiningar om.
