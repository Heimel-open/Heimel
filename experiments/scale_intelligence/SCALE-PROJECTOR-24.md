# SCALE-PROJECTOR-24 — Basis-invariant subspace intervention

Status before fresh execution: PREREGISTERED.

## Question

Does the invariant degenerate singular subspace implicated by SCALE-BASIS-23 carry an unusually strong scale-selective causal capability effect, independent of arbitrary SVD basis labels?

## Canonical base

`4d39c18f9b446f469d15458de02d0dcdd80fd623`

## Fixed target subspaces

Self-padded segmented block 13.

- scale 7 target right-singular subspace: the exact degenerate block spanning indices {6,7,8}, dimension 3;
- scale 13 target right-singular subspace: the exact degenerate block spanning indices {7,8,9,10,11}, dimension 5.

Only the orthogonal projectors onto these spans are used. Individual SVD vectors are not interpreted.

Fresh seeds:

`107107,108108,109109,110110,111111,112112,113113,114114,115115,116116`.

## Basis-invariant contribution

Let `B_s = P_C A_s^3 Q` be the centered input-to-central-output operator.

Let `P_s` be the orthogonal projector onto the fixed target right-singular subspace.

For centered input residual `r`:

`y_target = B_s P_s r`.

Because `r = P_s r + (I-P_s)r`, native central residual decomposes exactly into target-subspace and complement contributions.

## Causal intervention

Flip only the target-subspace contribution:

`y_flip = y_native - 2 y_target`.

All other residual components and the global/DC majority component remain native.

Define per-scale causal effect:

`E_s = capability_native_s - capability_flip_s`.

Define scale-selective target effect:

`DeltaE_target = E_13 - E_7`.

Positive DeltaE means the invariant target subspace is more capability-supporting at scale 13 than at scale 7.

## Dimension-matched random-subspace null

Construct the 62-dimensional centered input space orthogonal to the all-ones vector.

Generate exactly 1,000 deterministic Haar-random subspaces at each scale:

- dimension 3 for scale 7;
- dimension 5 for scale 13.

Use NumPy PCG64 seed `240024`. Random draws are paired by draw index across the two scales.

For every random projector `R_{s,q}`, apply the identical intervention:

`y_flip_random = y_native - 2 B_s R_{s,q} r`.

Compute:

`DeltaE_q = E_random_13,q - E_random_7,q`.

Primary one-sided empirical p:

`p = (1 + count(DeltaE_q >= DeltaE_target)) / 1001`.

No absolute effect-size threshold is imposed.

Classification:

- `PROJECTOR_EFFECT_OUTLIER_AGAINST_NULL` if DeltaE_target > 0 and p <= 0.05;
- `NOT_PROJECTOR_EFFECT_OUTLIER_AGAINST_NULL` otherwise.

Alpha=0.05 is the only inferential cutoff.

## Secondary basis-invariant task-overlap diagnostic

For each target projector:

`overlap_s = E[||P_s r||^2] / E[||r||^2]`.

Compare each target overlap to the corresponding 1,000 random dimension-matched projector overlaps. Report empirical percentile and p-value. This does not alter the primary result.

## Integrity

Only validity failures yield `INSUFFICIENT_EVIDENCE`:

- projector idempotence/symmetry error >1e-12;
- operator decomposition error >1e-12;
- target projector changes under 1,000 internal Haar basis rotations by >1e-12;
- incomplete fresh-seed coverage;
- null draw count/RNG mismatch.

## Interpretation boundary

A positive result supports only:

> the basis-invariant degenerate subspaces implicated by prior work have an unusually strong scale-selective causal effect compared with random subspaces of the same dimensions.

It does not yet identify why those subspaces are special. The task-overlap diagnostic distinguishes one candidate: preferential alignment with task residual structure.

No outcome-dependent subspace selection or thresholding is permitted.
