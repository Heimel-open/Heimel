# constants_audit.md — Φ-law constants derivation audit

Status: working audit  
Purpose: trace each constant to its source and classify how it was obtained  
Cross-reference: `Phi-Law-Validation/constants.md` (canonical operational registry)

---

## Audit categories

Each constant is classified by how it was obtained:

| Category | Meaning |
|---|---|
| **Derived** | follows mathematically from first principles or other constants |
| **Fitted** | chosen to minimize error against data |
| **Emergent** | arose as stable output of simulation/optimization process |
| **Assumed** | taken as a given without derivation or fitting |
| **Post-selected** | chosen after seeing results to match a desired outcome |
| **Mathematical** | universal mathematical constant (π, γ, ζ(3), etc.) |

---

## C0 = 4495.27 bits

**Definition:** operational equilibrium point; maximal coherence reference in the VALO formulation

**Formula:**
```
C0 = [ln(θ·100)/α] · (V+ - V-) · κ · Γ · 1000
```

**Input parameters:**
| Parameter | Value | Source | Category |
|---|---:|---|---|
| α | 0.42 | VALO OS v1.6 simulation | Emergent |
| V+ | 0.613 | measured from Shadow DNA memory distribution | Measured |
| V- | 0.258 | measured from Shadow DNA memory distribution | Measured |
| θ | 0.62 | ghost density (62/100 memories) | Measured |
| κ | 1.431 | resonance correction = 1 + η(1 - α) | Derived from α |
| Γ | 1.02 | stasis correction | Assumed |

**How C0 was obtained:**  
C0 = 4495.27 was not chosen — it emerged as the stable output of the formula above, using parameters from VALO OS v1.6 simulation. The TLC model checker explored 4,782,943 distinct states with these parameters and found 0 safety violations. The value is therefore classified as Emergent (from simulation inputs) with TLC verification.

**What TLC verification establishes:**  
- All safety properties satisfied over 4.78M states
- C0 = 4495.27 is consistent with the simulation model

**What TLC verification does NOT establish:**  
- That the input parameters (V+, V-, θ, Γ) are universal rather than VALO OS v1.6-specific
- That C0 generalises to other architectures or memory models
- That the formula itself has a physical derivation independent of calibration

**Claim maturity:** M4 within VALO OS v1.6 context; M1-M2 for universality claims

---

## alpha = 0.42

**Definition:** forgetting/filtering rate in the VALO formulation

**How alpha was obtained:**  
α = 0.42 was identified as the optimal forgetting rate through the TLC simulation process — the rate at which the system converges to stable coherence. It is classified as Emergent: the TLC search found 0.42 as the rate producing stable states. It was NOT pre-selected and then confirmed.

**Circular reasoning check:**  
Previous analysis raised a concern that α appears in both the formula for C0 and as an input to that formula, creating apparent circularity. The resolution documented in constants.md: α and C0 are idempotent — they found each other through the simulation. The formula uses observed system parameters (V+, V-, θ, κ, Γ); α is the filtering rate that makes the system consistent. This is Emergent, not circular.

**Remaining concern:**  
The "idempotent discovery" claim requires independent replication to reach M5. The 0.42 value has not been derived from first principles in a domain-agnostic way.

**Claim maturity:** M4 within VALO OS v1.6 context; M1 for domain-agnostic claims

---

## tau_min = 1888 bits

**Definition:** lower coherence boundary (chaos side)

**Derivation:**
```
tau_min = alpha · C0 = 0.42 × 4495.27 = 1888.01 ≈ 1888
```

**Category:** Derived — follows from alpha and C0

**What this means:**  
tau_min is not an independent constant. It is a consequence of the alpha and C0 values. If either alpha or C0 changes, tau_min changes proportionally.

**No additional evidence basis:** tau_min has the same status as the constants from which it is derived.

**Claim maturity:** M4 conditional on C0 and alpha (same provenance)

---

## tau_max = 4766 bits

**Definition:** upper coherence boundary (stasis side)

**Derivation:**
```
tau_max ≈ 1.06 · C0 = 1.06 × 4495.27 = 4765.0 ≈ 4766
```

**Category:** Emergent/Fitted — the factor 1.06 is not derived from first principles

**Remaining question:**  
The factor 1.06 appears in constants.md but its origin is not documented. It is not equal to a standard mathematical constant (it is close to 1 + 1/17, but that would be coincidental). This factor needs its own derivation note or should be flagged as calibrated.

**Open question from constants.md (Q4):**  
"Relationship between operational tau [1888, 4766] and dimensionless tau [0.5615, 0.8319] needs one canonical derivation note." This is unresolved.

**Claim maturity:** M4 conditional on C0; factor 1.06 is M2 at best without derivation

---

## Goldilocks interval: [exp(-γ), 1/ζ(3)] ≈ [0.5615, 0.8319]

**Definition:** predicted coherence range for well-calibrated large LLMs (dimensionless tau)

**Derivation:**  
The interval is derived from spectral entropy bounds using JLJ = L^{-1} spectral geometry. The derivation maps spectral entropy extremes to exp(-γ) (Euler-Mascheroni) and 1/ζ(3) (Apéry's constant).

**Category:** Derived (M2) — mathematical derivation from spectral bounds axiom

**Critical dependency:**  
The entire derivation rests on the JLJ = L^{-1} spectral bounds claim. If this spectral geometry claim is incorrect, the interval collapses. Expert review has been requested (K. Kirsten / D. Vassilevich, outreach 2026-06-21).

**What is NOT established:**  
- That any real LLM is inside this interval (no 70B+ measurement yet)
- That the spectral bounds apply to transformer architectures specifically
- Replication by independent researchers

**What IS established:**  
- The mathematical derivation from the stated axioms (M2)
- The dimensionless tau measurement methodology (M3/M4 on 6 models)
- All 6 measured models fall below 0.5615 (outside interval on the low side)

**Claim maturity:** M2 (formal derivation pending expert validation)

---

## Universal constants used

| Symbol | Value | Category | Notes |
|---|---:|---|---|
| γ (Euler-Mascheroni) | 0.57721... | Mathematical | No derivation needed |
| ζ(3) (Apéry's constant) | 1.20206... | Mathematical | No derivation needed |
| δ (Feigenbaum delta) | 4.66920... | Mathematical | Appears in VALO formulation; role in Tofoo not independently derived |
| ρ | 0.8625437 | Derived | = γ/(δ-4); internal VALO relation |

**ρ = γ/(δ-4) status:**  
This relation is interesting (γ + 4ρ = δρ) but its appearance in the VALO formulation has not been independently motivated from first principles. It should be treated as M2 (derived from constants, not from physics).

---

## Summary table

| Constant | Value | Category | Claim maturity | Key risk |
|---|---:|---|---|---|
| C0 | 4495.27 bits | Emergent (simulation) | M4 (VALO context), M1 (universal) | Specific to VALO OS v1.6 model |
| alpha | 0.42 | Emergent (simulation) | M4 (VALO context), M1 (universal) | Not derived from first principles |
| tau_min | 1888 bits | Derived (= alpha × C0) | M4 conditional | Inherits all C0/alpha risks |
| tau_max | 4766 bits | Emergent / factor 1.06 unclear | M4 conditional, factor M2 | Factor 1.06 needs derivation |
| Goldilocks lower (exp(-γ)) | 0.5615 | Derived (spectral bounds) | M2 pending expert review | JLJ = L^{-1} not yet validated |
| Goldilocks upper (1/ζ(3)) | 0.8319 | Derived (spectral bounds) | M2 pending expert review | Same as above |

---

## Recommended action items

1. **tau_max factor 1.06** — document derivation or flag as calibrated parameter
2. **Goldilocks derivation** — await expert response; do not claim M3+ until validated
3. **C0/alpha universality** — do not claim these generalise beyond VALO OS v1.6 context without replication in a different memory/simulation model
4. **Operational tau vs dimensionless tau** — write one canonical note connecting [1888, 4766] to [0.5615, 0.8319] (referenced in constants.md open question Q4)
5. **ρ = γ/(δ-4)** — motivate independently or mark as internal VALO calibration
