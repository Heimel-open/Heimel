# CLAIM_REGISTRY.md — Tofoo / Φ-loven / LIM

Status: working registry  
Purpose: prevent claims from exceeding evidence  
Rule: no claim may jump maturity levels without evidence  

---

## Maturity levels

| Level | Label | Meaning |
|---|---|---|
| M0 | Symbolic | narrative / cultural / philosophical meaning only |
| M1 | Conceptual | structural analogy — no formal derivation |
| M2 | Formal | mathematical derivation or schema |
| M3 | Simulated | simulation or architecture demonstrated |
| M4 | Empirical | measured on real systems |
| M5 | Replicated | independently replicated |
| M6 | Standardized | adopted in a standard or protocol |

---

## Core Φ-law claims

| ID | Claim | Layer | Maturity | Source | Evidence | Falsification condition |
|---|---|---|---|---|---|---|
| C-PHI-001 | There exists a coherence interval [tau_min, tau_max] for LLMs | architecture | M3/M4 | `Phi-Law-Validation/constants.md`, tau measurement notebooks | 6 models measured (GPT-2 → Qwen2.5-14B) | tau measurements outside [0.5615, 0.8319] (dimensionless) for large models |
| C-PHI-002 | tau scales as tau ≈ 0.10 × N^0.48 (cross-architecture) | empirical | M4 | `theory/2026-06-19-p10-tau-scaling-funn.md` | GPT-2, Phi-2, Mistral-7B measurements | scaling exponent inconsistent across independent measurement sets |
| C-PHI-003 | No current model is inside [0.5615, 0.8319]; entry predicted at ~70B+ | prediction | M3 | scaling law extrapolation | consistent with 6-model dataset | 70B measurement outside predicted range |
| C-PHI-004 | Goldilocks interval ≈ [exp(-γ), 1/ζ(3)] ≈ [0.5615, 0.8319] | formal | M2 | `Phi-Law-Validation/theory/` | spectral entropy bounds derivation | JLJ=L^{-1} spectral bounds shown invalid by K. Kirsten / D. Vassilevich |
| C-LIM-001 | Identity is what survives boundary-governed transformation over time | ontology | M0/M1 | Axiom A1 in `Phi-Law-Validation/axioms.md` | philosophical framing only; MUST NOT be used as evidence that a digital representation is the represented person | not falsifiable as stated — requires restatement with operational definition |
| C-LIM-002 | LIM provides the architectural principle bridging Tofoo meaning and VALO execution | architecture | M2 | `docs/TOFOO_TO_VALO_BRIDGE.md` | structural mapping documented | VALO executes correctly without any LIM-derived principle |

---

## Fleet routing claims (Vallikat / VectorPeak)

| ID | Claim | Layer | Maturity | Source | Evidence | Falsification condition |
|---|---|---|---|---|---|---|
| C-FR-001 | l(x) = 1 - exp(-πx²) is the governing latency function | model | M2 | internal Vallikat docs | assumed for all derived results | empirical routing data inconsistent with l(x) |
| C-FR-002 | Social optimum at x_opt = 1/sqrt(2π) ≈ 0.3989 | formal | M2 | `experiments/verify_fleet_routing_poa.py` | verified algebraically | objective/demand model corrected and x_opt changes |
| C-FR-003 | τ* = exp(-1/2) ≈ 0.6065 is the Pigouvian toll | formal | M2 | `experiments/verify_fleet_routing_poa.py` | verified: τ* = x_opt·l'(x_opt) ✓ | |
| C-FR-004 | l(x_opt) + τ* = 1 | formal | M2 | `experiments/verify_fleet_routing_poa.py` | verified algebraically ✓ | |
| C-FR-005 | PoA = 1.2622 | formal | M1 | internal Vallikat docs | recoverable under interpretation C only; standard denominator gives 6.09 | interpretation C shown to be nonstandard and not the social welfare objective |
| C-FR-006 | Post-toll PoA = 1 | claim | M1 | internal Vallikat docs | not verified — requires global proof | toll shown not to recover global optimum in CTMC simulation |
| C-FR-007 | τ* is arrival-rate invariant | formal | M2 (conditional) | internal R1 doc | conditional on Section 4 fluctuation decomposition — not yet rigorously derived from CTMC | Section 4 derivation shown incorrect |

---

## Multiscale state and governance claims

| ID | Claim | Layer | Maturity | Source | Evidence | Falsification condition |
|---|---|---|---|---|---|---|
| C-MSG-001 | In history-dependent governed workflows, preserving decision-relevant state and applying a separate authoritative correction should reduce boundary and tail errors compared with direct scalar-output prediction | architecture / hypothesis | M1 conceptual; M2 schema | `docs/theories/2026-08-02-neural-operators-rich-state-authoritative-correction.md` | External methodological support from Bhattacharya, arXiv:2605.08466; no VALO workflow test yet | On representative VALO workflows, rich-state + authoritative correction does not improve boundary/tail error, reproducibility or cross-granularity consistency against a direct-output baseline |

---

## J-space / workspace selection claims

| ID | Claim | Layer | Maturity | Source | Evidence | Falsification condition |
|---|---|---|---|---|---|---|
| C-JFS-001 | Controlled broad-scan, target-lock and disconfirming conditions produce phase-specific reorganization of sparse J-space contents, followed by a more stable decision-relevant candidate set | transformer workspace / hypothesis | M1 conceptual; M2 protocol | `docs/theories/2026-08-10-jspace-framleis-adaptive-cognitive-sweep.md` | Primary-source J-space observations + deterministic falsification harness; no empirical sweep run yet | Matched J-lens experiments show no target concentration, counterevidence recruitment, workspace reorganization or candidate stabilization beyond lexical/non-J-space controls |
| C-JFS-002 | Operationally stable J-space candidate sets and P10 tau inside the configured Goldilocks regime co-occur more reliably for coherent reasoning than matched failure controls | transformer workspace / hypothesis | M1 conceptual; M2 protocol | `docs/theories/2026-08-10-jspace-framleis-adaptive-cognitive-sweep.md`, `experiments/P10_Transformer_Workspace_Dynamics/README.md` | Harness keeps J-space stability and tau coupling independently falsifiable; empirical J-lens + tau run pending | Stable correct candidate sets systematically occur outside G, or tau lies inside G without decision-relevant J-space stabilization |

---

## Bounded self-ensemble / synthetic subconscious claims

| ID | Claim | Layer | Maturity | Source | Evidence | Falsification condition |
|---|---|---|---|---|---|---|
| C-BSE-001 | Multiple specialized bounded projections over one canonical representation can provide breadth by multiplicity and depth by specialization without creating multiple principals | personal twin / hypothesis | M1 conceptual; M2 schema | `docs/theories/2026-08-17-bounded-self-ensemble-synthetic-subconscious.md` | conceptual architecture only; no matched empirical comparison yet | matched heterogeneous decision tasks show no decision-relevant coverage/depth gain over a single general driver, or projections cannot remain separated from canonical representation state |
| C-BSE-002 | The smallest sufficient cognitive coalition should be preferred over always invoking the full ensemble because more answers are not necessarily better answers | adaptive deliberation / hypothesis | M1 conceptual; M2 objective schema | `docs/theories/2026-08-17-bounded-self-ensemble-synthetic-subconscious.md` | conceptual objective balancing quality, latency and human-attention cost; no preregistered test yet | fixed full-ensemble deliberation repeatedly provides materially better safety/decision quality after latency, compute and attention costs are controlled, or adaptive selection misses unacceptable high-impact concerns |
| C-SSC-001 | A governed synthetic-subconscious layer can perform background reasoning and surface only material novelty, contradiction or consequence, reducing foreground human attention without gaining authority | human attention / hypothesis | M1 conceptual; M2 architecture schema | `docs/theories/2026-08-17-bounded-self-ensemble-synthetic-subconscious.md` | functional architecture only; metaphor explicitly does not claim machine consciousness | matched workflows show background reasoning increases interruption, latency or false alarms without preserving decision quality/safety, or background outputs acquire ungoverned state/authority effects |
| C-FRL-001 | Predictability and representation continuity are independent dimensions: a surprising representation change may still be a trustworthy continuation if provenance, lineage, amendment basis and required representation invariants remain preserved | continuity / hypothesis | M1 conceptual; M2 schema | `docs/theories/2026-08-17-bounded-self-ensemble-synthetic-subconscious.md`, `docs/theories/2026-08-17-prediction-representation-continuity-authority.md`, `docs/theories/2026-08-17-representation-is-not-person.md` | current historical replay motivates the distinction, but no preregistered legitimate-novelty benchmark yet | preregistered continuity tests cannot distinguish surprising legitimate representation novelty from adversarial lineage drift better than simpler predictability/anomaly baselines |
| C-BSE-003 | Ensemble agreement, confidence or specialist competence must not be treated as authority; disagreement is evidence to synthesize or escalate, not a majority vote | authority separation / hypothesis | M1 conceptual | `docs/theories/2026-08-17-bounded-self-ensemble-synthetic-subconscious.md` | derived from canonical prediction/representation/continuity/authority separation; no runtime claim | a valid architecture requires ensemble consensus itself to create legitimate consequence-bearing authority, or separate authority evaluation adds no meaningful governance value |

---

## Representation continuity / person boundary claims

| ID | Claim | Layer | Maturity | Source | Evidence | Falsification condition |
|---|---|---|---|---|---|---|
| C-REP-001 | Personal-twin architecture can treat the digital twin strictly as a representation rather than the person while preserving prediction, portability, continuity and authority separation | digital twin / architecture hypothesis | M1 conceptual; M2 schema | `docs/theories/2026-08-17-representation-is-not-person.md`, `docs/theories/2026-08-17-prediction-representation-continuity-authority.md` | conceptual decomposition; no claim of metaphysical proof | a required personal-AI function repeatedly cannot be implemented or evaluated without collapsing representation into personal identity |
| C-DDNA-001 | Digital DNA can be operationalized as verifiable lineage of representation state through transformations, preserving provenance, integrity and declared invariants without claiming proof of personal identity | representation lineage / architecture hypothesis | M1 conceptual; M2 schema | `docs/theories/2026-08-17-representation-is-not-person.md` | formalized representation-state grammar; empirical lineage benchmark pending | lineage/provenance controls provide no measurable advantage over simpler state versioning for detecting silent rewrite, poisoning, cumulative drift or invalid amendments |
| C-REP-AUTH-001 | Fidelity, prediction accuracy, representation continuity, knowledge and ensemble consensus do not by themselves create consequence-bearing authority | authority separation / architecture hypothesis | M1 conceptual | `docs/theories/2026-08-17-representation-is-not-person.md`, `docs/theories/2026-08-17-prediction-representation-continuity-authority.md` | conceptual authority separation; no REHT runtime claim | legitimate consequence-bearing authority in representative test cases necessarily emerges from representation fidelity/consensus without any separately grounded principal, delegation, mandate or legal authority source |

---

## What Tofoo does NOT own

Tofoo defines language and conceptual structure only. Tofoo does not decide:

- runtime policy (→ VAIG)
- ACS/VACS semantics (→ vacs/)
- VALO L1 behavior (→ valo-v5-core)
- audit receipt format (→ vaig/rrp/receipt.py)
- authority graph (→ vaig/authority_gate.py)
- BARO signal thresholds (→ nsolland/baro)
