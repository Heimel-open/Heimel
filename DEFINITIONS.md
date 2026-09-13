# DEFINITIONS.md — Tofoo canonical terminology

Status: working registry  
Purpose: prevent term drift between README, manifesto, theory files, and VALO bridge  
Rule: if a term appears in code or receipts, its definition must be here  

---

## Core terms

| Term | Definition | Layer | Notes |
|---|---|---|---|
| **Φ-law** | The theoretical framework proposing a coherence interval for LLMs based on spectral entropy | theory | Mathematical status: M2 (formal derivation exists); empirical status: M4 (measured on 6 models) |
| **LIM** | Law of Identity Maintenance — the architectural principle that stable identity requires boundary-governed transformation | ontology/architecture | Bridges Tofoo ontology and VALO execution |
| **tau (τ)** | Coherence metric; dimensionless: τ = r_eff / r_max where r_eff = exp(H_spectral) | formal | Operational (bits): tau_min=1888, tau_max=4766. Dimensionless Goldilocks: [0.5615, 0.8319] |
| **C0** | Operational equilibrium point (4495.27 bits) — maximal coherence reference | operational | Private to Tofoo- and other private repos. Never hardcode in public repos |
| **alpha** | Forgetting/filtering rate (0.42) used in VALO formulation | operational | Private to Tofoo- and other private repos |
| **tau_min** | Lower coherence boundary (1888 bits; dimensionless: exp(-γ) ≈ 0.5615) | operational | Private to Tofoo- |
| **tau_max** | Upper coherence boundary (4766 bits; dimensionless: 1/ζ(3) ≈ 0.8319) | operational | Private to Tofoo- |
| **Goldilocks interval** | [exp(-γ), 1/ζ(3)] ≈ [0.5615, 0.8319] — predicted coherence range for well-calibrated LLMs | formal | Derived from spectral entropy bounds; pending expert validation |
| **Coherence** | A model's capacity to maintain consistent structured output over a conversation | formal | Measured via spectral entropy of token distribution |
| **Semantic collapse** | τ → 1 (maximum uncertainty) — model output loses structure | formal | Observed at ~14+ turns in MS Delegate-52 benchmark (GPT-4o 14.7% success after 20 steps) |
| **Identity** | What survives boundary-governed transformation over time (LIM Axiom A1) | ontology | M0/M1 — philosophical framing; operational definition required for falsifiability |

---

## VALO system mapping

| Tofoo layer | VALO equivalent | Notes |
|---|---|---|
| Meaning / symbol | Tofoo (this repo) | ontology and language |
| Law / principle | LIM | architectural constraint |
| Implementation | VAIG | runtime governance |
| Enforcement | VALO L1 | deterministic gate |
| Evidence | Janus / WORM | audit trail |
| Standardization | ACS / VACS | protocol |

Source: `docs/TOFOO_TO_VALO_BRIDGE.md` (if present) and Index VALO_SYSTEM_MAP.md

---

## What these terms are NOT

| Wrong usage | Correct usage |
|---|---|
| "Tofoo proves VALO" | "Tofoo supplies the ontology; VALO supplies the execution proof-of-work" |
| "LIM implies VALO L1 behavior" | "LIM is an architectural principle; L1 behavior is specified by formal verification" |
| "τ* proves the PoA claim" | "τ* is a locally verified Pigouvian toll; PoA = 1.2622 is conditional on an unverified denominator" |
| "Goldilocks interval is proven" | "Goldilocks interval is formally derived, pending expert validation of spectral bounds" |

---

## Truth type hierarchy

Use consistent language when citing claims:

- **Symbolic** — carries meaning, cannot fail
- **Analogy** — structurally similar, not formally equivalent
- **Derivation** — mathematically derived from stated axioms
- **Simulation** — shown in controlled numerical experiment
- **Measurement** — observed on real systems
- **Replication** — independently confirmed

Never conflate levels. A symbolic claim does not become stronger by citing a measurement in a different domain.
