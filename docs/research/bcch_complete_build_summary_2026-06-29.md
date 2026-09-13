# Boundary-Constrained Coherence Hypothesis — Build Summary

Date: 2026-06-29
Status: research prototype / toy-model support.

## Revised hypothesis

Original:

Stable identity requires a selective boundary operator F with contraction.

Revised:

Stable identity requires an active boundary operator with both selective filtering and return to the viable region Ω when perturbation exceeds local capacity.

Operational form:

```text
S_{t+1} = P_Ω(G(S_t, I_t) + A(S_t, H_t))
```

Where `G` is raw dynamics, `P_Ω` is boundary enforcement, `A` is restoring dynamics, and `Ω` is the viable identity region.

## Build A — Boundary sandbox

Five F variants were simulated:

- Null-F: diverged.
- Hard-F: stable.
- Soft-F with contraction only: can still diverge.
- Soft-F with clipping: stable.
- Adaptive-F: best stability.

Learning:

Contraction alone is not enough. Global stability needs active projection or return to Ω.

## Build B — Semantic Integrity Filter

The filter acts as a pre-update hook for AI agents:

```text
Instruction → Embedding → SemanticIntegrityFilter → ACCEPT / REJECT → Audit
```

It supports rejection, scaling, restoration toward Ω, and audit logging.

## Build C — falsification protocol

Toy test classes:

- reaction-diffusion pattern stability
- slime-network local repair
- unstable linear recurrent network
- noisy oscillator dynamics

Safe claim:

The revised hypothesis is supported within the toy-model simulations tested here.

Avoid claiming broad empirical validation across all domains.

## ACS / VAIG placement

Layering:

```text
BCC / Φ-law → theory
ACS → standard / protocol
VAIG → runtime architecture
VALO L1 → deterministic enforcement
Janus/WORM → evidence layer
```

## Stochastic correction

A boundary can preserve boundedness but not necessarily identity. Persistent noise can erase phase identity over time. A restoring component is therefore required in addition to the boundary.

## LLM persona drift experiment

A GPT-style autoregressive experiment was specified to measure hidden-state drift during token-by-token generation.

Measurements:

- cosine distance
- Euclidean distance
- geodesic trajectory length
- velocity
- acceleration
- alpha_proxy from AR(1) over PCA projection
- semantic proxy score

Safe language:

This estimates whether autoregressive hidden-state drift shows diffusive, subdiffusive, or attracting-like dynamics under persona-conditioned generation.

## Plain-language formulation

You are not stable because you never change.
You are stable because you have a boundary that chooses what you let in.

A boundary does not make you less. It keeps you you.
