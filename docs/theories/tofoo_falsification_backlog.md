# tofoo_falsification_backlog.md — Tofoo / Φ-law / LIM

Status: working backlog  
Purpose: enumerate falsification conditions for all tracked claims  
Rule: each test must state what outcome would REFUTE the claim, not confirm it

Cross-reference: `CLAIM_REGISTRY.md` for claim IDs and current maturity levels

---

## How to use this file

Each entry has:
- Claim ID (from CLAIM_REGISTRY.md)
- Testable condition
- Required data / hardware
- Failure outcome (what would falsify)
- Status

Do not add confirmatory evidence here — that belongs in CLAIM_REGISTRY.md.
This file tracks what would BREAK each claim.

---

## Φ-law / coherence claims

### F-PHI-001 — Coherence interval existence
Claim: C-PHI-001 — there exists a coherence interval [0.5615, 0.8319] for large LLMs

**Falsification test:**  
Measure dimensionless tau on 3+ models with N > 70B. If all measurements fall outside [0.5615, 0.8319], the prediction is wrong.

**Required:** RunPod A100 / H100 access; models Llama-3-70B, Qwen2.5-72B, Llama-3.1-405B

**Failure outcome:** Any well-calibrated 70B+ model with tau consistently outside [0.5615, 0.8319] across 3+ independent measurement runs

**Status:** Pending hardware access (see BARO #33 / Tofoo- #33)

---

### F-PHI-002 — Tau scaling law
Claim: C-PHI-002 — tau ≈ 0.10 × N^0.48 (cross-architecture)

**Falsification test:**  
Measure tau on 3+ architectures not in the current 6-model dataset. If exponent deviates more than ±0.05 from 0.48, or if the prefactor deviates more than ±0.03 from 0.10, the scaling law is not cross-architecture.

**Required:** New architectures (Mistral, Falcon, Gemma); minimum 3 model sizes per architecture family

**Failure outcome:** Scaling exponent outside [0.43, 0.53] or prefactor outside [0.07, 0.13] on a new independent architecture family

**Status:** Partially testable on open models — no 70B+ data yet

---

### F-PHI-003 — No model currently inside Goldilocks interval
Claim: C-PHI-003 — no current model is inside [0.5615, 0.8319]; entry predicted at ~70B+

**Falsification test:**  
Find any publicly available model (any size) with dimensionless tau consistently inside [0.5615, 0.8319] across 3+ conversation turns.

**Required:** Measurement notebooks (tau_colab.ipynb) run on candidates

**Failure outcome:** Any existing model (including sub-7B) measured inside [0.5615, 0.8319]

**Status:** Ongoing — 6 models measured, none inside interval

---

### F-PHI-004 — Goldilocks interval derivation
Claim: C-PHI-004 — Goldilocks interval = [exp(-γ), 1/ζ(3)] ≈ [0.5615, 0.8319]

**Falsification test:**  
Expert mathematical review of JLJ = L^{-1} spectral bounds argument. If K. Kirsten or D. Vassilevich (or any operator theorist) identifies an error in the spectral entropy bound derivation, the formal derivation (M2) is downgraded to M1.

**Required:** Response from expert outreach (K. Kirsten / D. Vassilevich — drafts sent 2026-06-21)

**Failure outcome:** Expert identifies an error in JLJ = L^{-1} → [exp(-γ), 1/ζ(3)] derivation

**Status:** Awaiting expert response

---

### F-LIM-001 — Identity axiom (LIM A1)
Claim: C-LIM-001 — identity is what survives boundary-governed transformation over time

**Falsification test:**  
This claim is currently M0/M1 — not formally falsifiable as stated. The required step is: produce an operational definition of "identity" that allows a yes/no test on any boundary-governed transformation. Without that, this claim cannot be falsified.

**Required:** Operational definition + proposed test protocol

**Failure outcome:** Not applicable until claim is restated with operational definition

**Status:** Awaiting reformulation — cannot be falsified in current form

---

### F-LIM-002 — LIM bridges Tofoo and VALO
Claim: C-LIM-002 — LIM provides the architectural principle bridging Tofoo meaning and VALO execution

**Falsification test:**  
Show that VALO executes correctly without any LIM-derived principle. Specifically: demonstrate a working VALO runtime (VAIG) where no LIM-derived constraint is active, and the runtime still maintains its governance invariants.

**Required:** VAIG runtime without LIM-derived evidence gating — theoretical analysis or implementation test

**Failure outcome:** VAIG maintains all governance invariants without LIM-derived constraints

**Status:** Not yet tested — requires formal analysis of VAIG dependency structure

---

## Fleet routing claims

### F-FR-001 — Latency function form
Claim: C-FR-001 — l(x) = 1 - exp(-πx²) is the governing latency function

**Falsification test:**  
Collect empirical routing data from Vallikat/VectorPeak deployment. Fit l(x) to measured latency-vs-load data. If goodness-of-fit R² < 0.9, the functional form is wrong.

**Required:** Empirical routing data from production system

**Failure outcome:** R² < 0.9 on fit of l(x) = 1 - exp(-πx²) to real routing latency data

**Status:** No empirical data available — claim remains M2 (model only)

---

### F-FR-002 — Social optimum
Claim: C-FR-002 — social optimum at x_opt = 1/sqrt(2π) ≈ 0.3989

**Falsification test:**  
If the demand model or objective function is corrected and x_opt changes, the claim fails. Current derivation assumes an unspecified demand model — specify and verify.

**Required:** Explicit demand model specification + optimization derivation

**Failure outcome:** Demand model corrected → x_opt deviates from 0.3989

**Status:** Algebraically verified given the latency function — demand model remains underspecified

---

### F-FR-003 — Pigouvian toll identity
Claim: C-FR-003 — τ* = exp(-1/2) ≈ 0.6065 is the Pigouvian toll

**Falsification test:**  
τ* = x_opt · l'(x_opt) is algebraically verified (see experiments/verify_fleet_routing_poa.py). This identity cannot be false given the latency function. The real falsification condition: if the demand model changes, x_opt changes, and τ* changes accordingly.

**Required:** Specification of demand model

**Failure outcome:** Different demand model gives different x_opt → different τ*

**Status:** Local identity verified (PASS in verify_fleet_routing_poa.py Section 3)

---

### F-FR-004 — Complementarity condition
Claim: C-FR-004 — l(x_opt) + τ* = 1

**Falsification test:**  
Algebraically verified as exact identity given l(x) = 1 - exp(-πx²). Cannot be false given this functional form.

**Required:** Not applicable — this is a mathematical consequence

**Failure outcome:** Not falsifiable given the latency function

**Status:** VERIFIED algebraically (verify_fleet_routing_poa.py Section 3)

---

### F-FR-005 — PoA = 1.2622
Claim: C-FR-005 — price of anarchy = 1.2622

**Falsification test:**  
Three interpretations tested in verify_fleet_routing_poa.py. Standard denominator (x_opt · l(x_opt)) gives PoA = 6.09. The claim PoA = 1.2622 is recoverable only under interpretation C (denominator = 1 - exp(-0.5)/sqrt(2π)). Show that interpretation C equals the true social welfare objective — or the claim fails.

**Required:** Explicit social welfare objective derivation showing denominator = 1 - exp(-0.5)/sqrt(2π)

**Failure outcome:** Social welfare objective confirmed as standard (x_opt · l(x_opt)) → PoA = 6.09, not 1.2622

**Status:** UNVERIFIED — interpretation C is nonstandard and ungrounded; see verify_fleet_routing_poa.py

---

### F-FR-006 — Post-toll PoA = 1
Claim: C-FR-006 — post-toll price of anarchy = 1

**Falsification test:**  
Show via CTMC simulation or formal proof that the Pigouvian toll τ* recovers the global social optimum. Current CTMC simulation indicates this does NOT hold globally.

**Required:** Formal global optimality proof or corrected CTMC simulation

**Failure outcome:** CTMC simulation confirms toll does not recover global optimum (already observed)

**Status:** LIKELY FALSE — CTMC simulation shows toll does not recover global optimum

---

### F-FR-007 — Arrival-rate invariance
Claim: C-FR-007 — τ* is arrival-rate invariant

**Falsification test:**  
Derive the fluctuation decomposition from Section 4 of the R1 document rigorously from CTMC. If the derivation is incorrect or τ* depends on arrival rate in the CTMC model, the claim fails.

**Required:** Rigorous Section 4 CTMC derivation

**Failure outcome:** τ* shown to depend on arrival rate in CTMC model; or Section 4 derivation found incorrect

**Status:** Conditional M2 — derivation not yet rigorous

---

## J-space / Framleis workspace-selection claims

### F-JFS-001 — Adaptive sweep phase signatures
Claim: C-JFS-001 — controlled search conditions produce phase-specific J-space reorganization followed by a stable candidate set

**Falsification test:**  
Run a pre-registered multi-task J-lens experiment with matched lexical/task controls and, where instrumentable, matched non-J-space directions. Measure normalized target mass, workspace concentration, disconfirming mass, weighted workspace turnover and repeated candidate-set stability.

**Required:** J-lens compatible model/instrumentation; raw per-layer/token sparse J-space coordinates; independent target/counterevidence labels; matched prompt/task controls; pre-registered thresholds and aggregation.

**Failure outcome:** TARGET_LOCK does not increase target mass/concentration; DISCONFIRMING_SWEEP does not recruit counterevidence or reorganize J-space; repeated CANDIDATE_SET readouts do not stabilize; or lexical/non-J-space controls reproduce the same effects.

**Status:** Executable deterministic falsifier + synthetic mechanics tests implemented; empirical J-lens run pending. Synthetic test success is not evidence for the claim.

---

### F-JFS-002 — J-space / P10 spectral coupling
Claim: C-JFS-002 — operationally stable J-space candidate sets and tau inside configured G co-occur for coherent reasoning more reliably than matched failure controls

**Falsification test:**  
Measure J-space candidate-set stability and tau independently on the same traces. Do not infer one from the other.

**Required:** Same data as F-JFS-001 plus P10 tau extraction and a Goldilocks band fixed before evaluation.

**Failure outcome:** Stable correct candidate sets systematically occur outside G, or tau is inside G while decision-relevant J-space content fails to stabilize.

**Status:** Harness independently tests workspace stability and spectral coupling; empirical paired run pending.

---

## Priority ordering

| Priority | Test | Reason |
|---|---|---|
| High | F-JFS-001 (adaptive sweep J-lens run) | Directly tests the newly exposed mechanism gap: what selects J-space content |
| High | F-JFS-002 (paired J-space + tau run) | Separates workspace stabilization from the existing P10 spectral hypothesis |
| High | F-PHI-004 (expert review) | Awaiting response — external dependency |
| High | F-FR-005 (PoA denominator) | Core claim, currently unverified |
| High | F-FR-006 (post-toll PoA) | Already likely false — needs documentation |
| Medium | F-PHI-001 (70B measurement) | Hardware required |
| Medium | F-PHI-002 (scaling law) | New architectures needed |
| Medium | F-FR-007 (arrival-rate invariance) | Derivation gap |
| Low | F-LIM-001 (reformulation) | Conceptual — no new data needed |
| Low | F-FR-001 (empirical data) | Production data not available |

---

## What this backlog does not cover

- Claims not yet registered in CLAIM_REGISTRY.md
- Model-specific calibration (substrate-specific K measurements)
- VAIG runtime governance claims (those belong in VAIG TEST_EVIDENCE.md)
- τ scaling across new domains outside LLMs
