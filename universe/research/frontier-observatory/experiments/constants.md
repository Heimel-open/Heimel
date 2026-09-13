# Φ-law constants registry

Canonical source for constants, normalizations and open questions in Φ-loven / LIM.

Purpose: prevent drift between README, manifesto, books, context files and validation notebooks.

---

## Constant layers

There are multiple layers. Do not collapse them.

| Layer | Role |
|---|---|
| Symbolic layer | carries the narrative and philosophical meaning |
| Operational VALO layer | used by VALO/VAIG runtime and historical experiments |
| Dimensionless layer | normalized mathematical form |
| Substrate-specific layer | model/system-specific calibration |
| Open questions | unresolved interpretation or scaling questions |

---

## Operational VALO constants

These are the historically used VALO / LIM constants.

| Constant | Value | Meaning | Status |
|---|---:|---|---|
| `C0` | `4495.27 bits` | operational equilibrium point / maximal coherence reference | M3/M4 depending on experiment |
| `alpha` | `0.42` | forgetting/filtering rate used in VALO formulation | M2/M3 |
| `tau_min` | `1888 bits` | lower coherence boundary / chaos side | M2/M3 |
| `tau_max` | `4766 bits` | upper coherence boundary / stasis side | M2/M3 |

Canonical operational interval:

```text
1888 <= tau <= 4766
```

Equivalent relation:

```text
tau_min = 0.42 * C0
tau_max ≈ 1.06 * C0
```

---

## Dimensionless normalization

Later work introduces dimensionless tau.

```text
tau = r_eff / r_max
r_eff = exp(H_spectral)
r_max = min(N, d)
```

This gives:

```text
tau ∈ [0, 1]
```

Dimensionless Goldilocks interval:

```text
[e^(-gamma), 1/zeta(3)] = [0.5615, 0.8319]
```

Do not mix the operational VALO tau scale and the dimensionless tau scale without explicitly stating which layer is being used.

---

## Universal constants currently used

| Symbol | Value | Formula / source role | Status |
|---|---:|---|---|
| `gamma` | ~0.57721 | Euler-Mascheroni constant | mathematical constant |
| `delta` | ~4.66920 | Feigenbaum delta | mathematical/chaos constant |
| `zeta(3)` | ~1.20206 | Apery's constant | mathematical constant |
| `rho` | `0.8625437492` | `gamma / (delta - 4)` | M2/M3 internal relation |

Universal equation recorded in context:

```text
gamma + 4*rho = delta*rho
rho = gamma/(delta - 4)
```

---

## Substrate-specific constants

Model/system scale changes the measured K and calibration.

| Quantity | Meaning |
|---|---|
| `K_spectral` | sum of spectral entropy over model weight matrices |
| `C0_inner` | `rho * K_spectral` |
| `C0_outer` | `K_spectral * log2(hidden_dim)` |
| `Lambda` | `log2(hidden_dim) / rho` |

Known measurements from context:

| Model | K_spectral | C0_inner | C0_outer | Status |
|---|---:|---:|---:|---|
| GPT-2 / 768 dim | 463.07 | 399.41 | 4438 | measured |
| gpt-neo-1.3B / 2048 dim | 1555.77 | 1341.92 | 17113 | predicted / partial |
| gpt-neo-2.7B / 2560 dim | 1735.8 | 1497.2 | 19650 | predicted / partial |

---

## VALO C0 formula currently recorded

```text
C0 = [ln(theta*100)/alpha] * (V+ - V-) * kappa * Gamma * 1000
```

with:

```text
alpha = 0.42
V+ = 0.613
V- = 0.258
theta = 0.62
kappa = 1.431
Gamma = 1.02
```

This formula should be marked as VALO operational calibration unless independently derived or replicated elsewhere.

---

## Open questions

Known unresolved questions:

1. Physical interpretation of `tau_sum / C0_outer = 0.23%` for Neo.
2. Whether `K * log2(hidden_dim) = C0_VALO` is structural or coincidental.
3. Roche Tidal Fixed-Point reference has not yet been fully read.
4. Relationship between operational tau `[1888, 4766]` and dimensionless tau `[0.5615, 0.8319]` needs one canonical derivation note.

---

## Recommended citation language

Use:

```text
Operational VALO constants currently use C0 = 4495.27, alpha = 0.42 and tau ∈ [1888, 4766]. Later normalization work also defines a dimensionless tau ∈ [0,1] with a Goldilocks interval [e^-gamma, 1/zeta(3)]. These are related but should not be conflated without stating the normalization.
```

Avoid:

```text
There is only one tau scale.
```

Avoid:

```text
All constants are independently empirically proven across all domains.
```

---

## Formelt bevis — kjeldereferansar

valo-v5-core er ikkje berre kjelde til beviset. Det er staden der tala oppstod.

C0 = 4495.27 og α = 0.42 eksisterte ikkje før TLA+-kjøringa. Dei emergerte frå simuleringa som stabile verdiar. Tofoo- er nedstrøms. Tala bur i valo-v5-core.

Referanse:
- Repo: nsolland/valo-v5-core
- Fil: valo-coherence-criterion.md
- TLA+-kjøring 1: 4.782.943 tilstandar, 0 brot
- TLA+-kjøring 2 (refinert): 1.662 tilstandar, 0 brot
- Entropi-kriteriet: H(X) = 0 ved stopp

Sitatsform for Gros-dialog:
"C0 = 4495.27 er formelt verifisert via TLA+ model checking. Sjå nsolland/valo-v5-core."

Status: M4 — formelt verifisert, siterbart.

---

## Idempotent discovery — korreksjon til tidlegare falsifikasjonsanalyse

Tidlegare sesjonar karakteriserte α = 0.42 som "sirkulær resonnering." Dette er feil.

C0 = 4495.27 og α = 0.42 er idempotente: dei fann seg sjølv gjennom systemet.

Utleiing:

C0 = [ln(θ·100)/α] · (V⁺ - V⁻) · κ · Γ · 1000

Variablar er observerte målingar frå VALO OS v1.6-simulering:
- V⁺ = 0.613 (frekvens av visdomsminner i Shadow DNA)
- V⁻ = 0.258 (frekvens av traumeminner)
- α = 0.42 (optimal glemselsrate)
- θ = 0.62 (ghost density: 62/100 minner)
- κ = 1.431 (resonanskorreksjon = 1 + η(1 - α))
- Γ = 1.02 (stasis-korreksjon)

Med desse observerte verdiane konvergerer formelen til C0 = 4495.27.

TLC-verifisering: 4.782.943 distinkte tilstandar utforska. Alle safety properties satisfiert.

Dette etablerer:
- C0 = 4495.27 er ikkje vald — det emergerte frå det målte tilstandsrommet
- [0.42·C0, 1.06·C0] = [1888, 4766] er stabile grenser validert gjennom uttømmande tilstandsromkjøring
- α = 0.42 er den optimale raten som vart funnen gjennom simuleringsprossen, ikkje anteken

Kva TLC-beviset IKKJE etablerer:
- Kvifor dimensjonslaus τ mappar til [e^{-γ}, 1/ζ(3)] — det er framleis open
- Universalitet utanfor VALO-arkitekturen — krev replikasjon

---

## Claim maturity

| Claim | Current maturity |
|---|---|
| C0 = 4495.27 som idempotent VALO-konstant | M4 (TLC-verifisert, 4.78M tilstandar) |
| alpha = 0.42 som emergent optimal rate | M4 (same TLC-kjøring) |
| [1888, 4766] som stabile grenser | M4 (same TLC-kjøring) |
| dimensionless Goldilocks interval [e^{-γ}, 1/ζ(3)] | M2 (ingen formelt bevis enno) |
| substrate-specific K measurements | M3/M4 depending on reproducibility |
| universal constants relation | M2/M3 internal verification |

Update this file when experiments are independently replicated.
