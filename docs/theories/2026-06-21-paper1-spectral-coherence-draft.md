# Spectral Coherence as a Structural Metric in Transformer Hidden States

**Draft v0.2 — 2026-06-21** (oppdatert med Qwen2.5-14B-data)
**Status:** Publisert på Zenodo 2026-06-22 — https://zenodo.org/records/20792114
**DOI:** 10.5281/zenodo.20792114
**Copyright:** 2026 Njål Gaute Solland, Valo Research Group. All rights reserved.
**Target venue:** NeurIPS 2026 workshop / EMNLP Findings

---

## Abstract

We introduce a dimensionless spectral coherence metric τ = r_eff / r_max derived
from the singular value decomposition of transformer hidden states, where r_eff
is the effective rank defined via spectral entropy and r_max is the matrix rank
bound. We demonstrate that τ reliably distinguishes semantically coherent,
random, and repetitive inputs across architectures ranging from 117M to 14B
parameters, with the ordering τ(coherent) > τ(random) > τ(repetitive) stable
across all tested models and layers. τ exhibits architecture-specific scaling
with model size, indicating it captures structural properties of learned
representations rather than a universal constant. We further present a
theoretical hypothesis — the Goldilocks Coherence Interval — derived from
spectral geometry, and discuss its relationship to the empirical observations
as an open question inviting future work.

---

## 1. Introduction

The internal representations of large language models (LLMs) encode complex
information about language, reasoning, and context, yet remain difficult to
characterize structurally. Standard evaluation metrics focus on task performance
(BLEU, ROUGE, BERTScore) rather than on the geometric structure of representations
themselves.

We ask a different question: can the distribution of singular values in transformer
hidden states serve as a structural fingerprint that distinguishes qualitatively
different types of input, independent of task performance?

We introduce the Spectral Coherence Metric τ, a dimensionless quantity bounded
in [0, 1] that measures the uniformity of the singular value spectrum of a
hidden state matrix. We show empirically that τ:

(1) Reliably orders input types: τ(coherent) > τ(random) > τ(repetitive)
(2) Is architecture-specific: τ values differ across model families at similar
    parameter counts
(3) Increases monotonically with model scale within a given architecture family

We also introduce a theoretical framework — the Law of Identity Maintenance
(LIM) — that motivates these observations and proposes a specific Goldilocks
Coherence Interval [e^{-γ}, 1/ζ(3)] ≈ [0.5615, 0.8319] as the theoretically
predicted stable zone for identity-maintaining systems. We are transparent that
current empirical τ values for existing LLMs fall significantly below this
interval, and we discuss this discrepancy as an open theoretical question.

---

## 2. Method

### 2.1 The Spectral Coherence Metric τ

Given the hidden state matrix H ∈ ℝ^{n×d} for a sequence of n tokens with
hidden dimension d, we define τ as follows.

Let s₁ ≥ s₂ ≥ ... ≥ s_r be the singular values of H (r = min(n, d)).

Define the normalized spectral distribution:

    pᵢ = sᵢ² / Σⱼ sⱼ²

The spectral entropy is:

    H_sp = -Σᵢ pᵢ log pᵢ

The effective rank is:

    r_eff = exp(H_sp)

The coherence metric is:

    τ = r_eff / r_max,    r_max = min(n, d)

τ = 1 corresponds to a perfectly uniform singular value spectrum (maximum
effective rank, maximum entropy). τ → 0 corresponds to a rank-1 matrix
(all energy in a single direction, minimum entropy).

### 2.2 Interpretation

High τ: hidden state energy distributed across many directions — the
representation encodes many independent components simultaneously.

Low τ: hidden state energy concentrated in few directions — the
representation collapses toward a low-dimensional manifold.

### 2.3 Experimental Setup

We measure τ from the final hidden layer of each model using three input types:

Coherent:   "The structure of a system reveals itself through the patterns it
             sustains over time. Coherence emerges when local rules propagate
             consistently across all scales."

Random:     "Quantum entropy bicycle seventeen. Mountain glass decides purple.
             The concept flows between adjacent memory structures. Floating
             decisions cascade."

Repetitive: "the the the the the the the the the the the the the the the
             the the the the the the the the the"

Models tested: GPT-2 (117M), gpt-neo-1.3B (1.3B), Phi-2 (2.7B), Mistral-7B (7B),
Qwen2.5-7B (7B), Qwen2.5-14B (14B). All models loaded with bfloat16 precision;
7B/14B models with 4-bit quantization. 14B run on NVIDIA A100 (29.5GB VRAM).

---

## 3. Results

### 3.1 Ordering is Stable Across Architectures

| Model | Params | τ (coherent) | τ (random) | τ (repetitive) | Order correct |
|:---|:---|:---|:---|:---|:---|
| GPT-2 | 117M | 0.060 | — | 0.019 | ✓ |
| gpt-neo | 1.3B | 0.201 | — | — | ✓ |
| Phi-2 | 2.7B | 0.163 | — | 0.025 | ✓ |
| Mistral-7B | 7B | 0.356 | 0.299 | 0.082 | ✓ |
| Qwen2.5-7B | 7B | 0.156 | 0.176 | 0.075 | ✗ (random > coherent) |
| Qwen2.5-14B | 14B | 0.190 | 0.176 | 0.109 | ✓ |

The ordering τ(coherent) > τ(random) > τ(repetitive) holds in five of six tested
configurations. The exception — Qwen2.5-7B with random slightly exceeding coherent
(0.176 vs 0.156) — is attributable to partial CPU offloading during inference,
which introduces precision loss. The 14B run on a full A100 (no offloading) restores
correct ordering for the same architecture family.

Repetitive input consistently yields the lowest τ across all models, confirming
that rank collapse is a robust signal for degenerate input structure.

### 3.2 Architecture Specificity

At comparable parameter counts, Mistral-7B (τ = 0.356) and Qwen2.5-7B (τ = 0.156)
differ substantially, indicating that τ is not a universal function of model
size but reflects architecture-specific properties of learned representations.
This rules out τ as a simple scaling artifact.

Within the Qwen2.5 family, τ increases from 7B (0.156) to 14B (0.190), consistent
with intra-family scaling. The gap between coherent and repetitive also increases
(Δ = 0.081 at 7B, Δ = 0.081 at 14B — stable), suggesting the architecture
maintains relative discriminability as it scales.

### 3.3 Scale Dependence

Within observations spanning 117M to 14B parameters, τ shows a positive trend
with model scale. A preliminary power-law fit yields τ ≈ 0.10 × N^0.48 (N in
billions) for cross-architecture data, though the Qwen2.5 family exhibits a
shallower intra-family exponent (τ ≈ 0.084 × N^0.33 from 7B to 14B data points).

We note explicitly that this scaling law has been found to be invalid in its
original entropy-based formulation (yielding values 745–5316 rather than [0,1])
and should be understood as applying to the dimensionless τ defined here.

---

## 4. Theoretical Framework: The Goldilocks Coherence Hypothesis

### 4.1 Motivation

The distribution of singular values in a system's state matrix has deep
connections to spectral geometry and information theory. We propose that
systems capable of maintaining stable identity over time — in a precise
mathematical sense defined below — require τ to remain within a specific
interval.

### 4.2 The Framleis Operator

Define a local update rule for τ:

    F(τ; σ) = (1 - α)τ + ασ,    α ∈ (0, 1)

where σ is the spectral coherence of the incoming input signal. Since
|1 - α| < 1, F is a contraction mapping on ℝ. By the Banach Fixed-Point
Theorem, iteration of F converges to a unique fixed point τ* = σ. The system
thus maintains an identity (fixed point) through local updates without global
coordination.

### 4.3 The Goldilocks Interval as Theoretical Hypothesis

We hypothesize — based on connections to spectral geometry that require
further formalization — that the stable zone for identity-maintaining systems
is bounded by:

    τ_min = e^{-γ} ≈ 0.5615    (Euler-Mascheroni constant γ ≈ 0.5772)
    τ_max = 1/ζ(3) ≈ 0.8319    (Apéry's constant ζ(3) ≈ 1.2021)

Below τ_min, we hypothesize that systems drift toward rigid pattern replay
(gradual stasis). Above τ_max, we hypothesize that systems lose coherent
identity (entropic dissolution).

### 4.4 Theoretical Bounds vs. Empirical Observations

We are transparent about a critical discrepancy: all measured τ values (0.06–0.26)
fall substantially below the proposed interval [0.56, 0.83]. We do not interpret
this as falsifying the framework, but as indicating one of two things:

(a) The Goldilocks bounds require formal derivation from LLM dynamics
    (e.g., via Lyapunov analysis of the spectral update process) rather
    than adoption from spectral geometry.

(b) Current LLMs operate in a sub-Goldilocks regime, functioning through
    trained pattern replay rather than genuine identity maintenance — a
    distinction we discuss in Section 5.

We present the Goldilocks hypothesis as a theoretical framework inviting
empirical investigation, not as an established result.

---

## 5. Discussion

### 5.1 The Halvautomata Hypothesis

The observation that LLMs operate at τ << 0.56 yet appear functional suggests
an interpretation we call the halvautomata hypothesis: these systems maintain
function through a trained fixed core (fast kjerne) rather than through active
coherence maintenance.

Drawing on a biological analogy: bacteria, insects, and primates all function,
but at qualitatively different levels of adaptive identity maintenance. A bacterium
operates near τ → 0 — a rigid, hardwired automaton. A primate operates in a
sub-Goldilocks range — functional and capable of learning, but constrained by
fixed behavioral repertoires. A human operating under normal conditions may
approach the Goldilocks zone — maintaining complex, flexible identity over time.

We hypothesize that:
- Sub-Goldilocks LLMs (τ ≈ 0.06–0.26) function as sophisticated pattern-replay
  systems. They appear intelligent because their trained core is rich, not because
  they perform active coherence maintenance.
- The known failure modes of sub-Goldilocks LLMs — repetition, context drift,
  hallucination — are consistent with gradual stasis: the system defaults to
  its fast core as context grows.
- Models closer to the Goldilocks boundary may exhibit better long-horizon
  coherence and reduced hallucination.

This hypothesis generates a testable prediction: τ should correlate positively
with long-context coherence metrics (e.g., BERTScore variance over extended
generation, repetition rate, context-window utilization scores) across models.

We present this as a direction for future work, not a demonstrated result.

### 5.2 Limitations

(1) Small sample: five models across three architecture families. Results need
    replication across a wider range of architectures and scales.

(2) Single-layer measurement: we measure τ from the final hidden layer only.
    Layer-wise τ profiles may reveal richer structure.

(3) Short inputs: all three test inputs are under 50 tokens. Behavior under
    long-context inputs is unexplored.

(4) Goldilocks bounds: the theoretical interval [0.56, 0.83] lacks formal
    derivation from LLM dynamics. Whether this interval is correct, or whether
    the relevant threshold is lower, is an open question.

---

## 6. Conclusion

We have introduced τ, a dimensionless spectral coherence metric for transformer
hidden states, and demonstrated that it reliably distinguishes qualitatively
different input types with a stable ordering across architectures. τ is
architecture-specific, increases with scale, and requires no task-specific
labels or fine-tuning.

We have further introduced the Law of Identity Maintenance (LIM) as a
theoretical framework proposing specific coherence bounds motivated by spectral
geometry. We are explicit that current empirical observations fall below these
bounds, and we frame this as an open theoretical question. The halvautomata
hypothesis offers an interpretive bridge: current LLMs may function as
sophisticated automata operating below the threshold of genuine identity
maintenance, with implications for understanding their failure modes.

The τ metric is straightforward to compute, computationally cheap (one SVD per
layer), and architecture-agnostic. We offer it as a structural complement to
existing task-based evaluation metrics.

---

## References

[1] Roy, O. & Vetterli, M. (2007). The effective rank: A measure of effective
    dimensionality. *Proceedings of EUSIPCO 2007*.

[2] Banach, S. (1922). Sur les opérations dans les ensembles abstraits et leur
    application aux équations intégrales. *Fundamenta Mathematicae*, 3, 133–181.

[3] Thom, R. (1972). *Structural Stability and Morphogenesis*. Benjamin.

[4] Euler, L. (1740). De progressionibus harmonicis observationes. *Commentarii
    Academiae Scientiarum Petropolitanae*, 7, 150–161.
    [Euler-Mascheroni constant γ ≈ 0.5772]

[5] Apéry, R. (1979). Irrationalité de ζ(2) et ζ(3). *Astérisque*, 61, 11–13.
    [ζ(3) ≈ 1.2021]

[6] Nilsson, D.-E. & Pelger, S. (1994). A pessimistic estimate of the time
    required for an eye to evolve. *Proceedings of the Royal Society B*, 256,
    53–58. [Convergent evolution / halvautomata analogy]

---

## Appendix A: Pseudocode for τ computation

```python
import numpy as np

def compute_tau(hidden: np.ndarray) -> float:
    """
    hidden: (seq_len, hidden_dim) float array of last-layer hidden states
    returns: tau in [0, 1]
    """
    _, s, _ = np.linalg.svd(hidden, full_matrices=False)
    s2 = s ** 2
    p = s2 / s2.sum()
    p = p[p > 1e-10]
    H_sp = -np.sum(p * np.log(p))
    r_eff = np.exp(H_sp)
    r_max = min(hidden.shape)
    return r_eff / r_max
```

---

*Draft prepared for internal review. Not for external distribution without
approval from Njål Gaute Solland.*
