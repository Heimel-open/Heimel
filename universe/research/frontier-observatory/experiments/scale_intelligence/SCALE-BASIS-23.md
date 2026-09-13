# SCALE-BASIS-23 — Degenerate-SVD basis invariance audit

Status before execution: PREREGISTERED.

## Why this audit is necessary

SCALE-PAIR-PHASE-22 identified pair (6,7) using thin-SVD mode labels.

Direct inspection of the frozen operators shows exact singular-value degeneracy:

Scale 7:
- modes 6,7,8 share the same singular value (~0.33196788).

Scale 13:
- modes 7,8,9,10,11 share the same singular value (~0.63582120).

Inside an exactly degenerate singular subspace, the SVD basis is not unique. Any orthogonal rotation applied jointly to the corresponding left and right singular vectors leaves the transfer operator unchanged.

Therefore an individual mode label inside such a block is not a basis-invariant physical object.

## Canonical base

`79efda1eef41948b9a7b1317ada355ceea3b501d`

## Fixed audit target

- self-padded segmented block 13;
- scales 7 and 13;
- pair label (6,7);
- reuse SCALE-PAIR-PHASE-22 episode seeds only for deterministic representation audit:
  `97097..106106`.

This is not a new out-of-sample capability claim. Native system outputs must be identical under every basis rotation.

## Degenerate blocks

Detect maximal contiguous singular-value blocks using exact numerical tolerance:

`abs(s_i - s_j) <= 1e-12 * max(1, abs(s_i), abs(s_j))`.

Only blocks containing mode 6 or 7 are rotated:

- scale 7: block {6,7,8};
- scale 13: block {7,8,9,10,11};
- scale-13 mode 6 is outside that degenerate block and remains fixed.

## Intervention

Generate 1,000 deterministic Haar-orthogonal rotations per scale/block using NumPy PCG64 seed `230023`.

For a degenerate block with common singular value sigma and orthogonal rotation R:

`U_block -> U_block R`
`V_block -> V_block R`

with singular values unchanged.

This preserves `U Sigma V^T` exactly up to floating-point tolerance.

For every rotated basis:

1. verify transfer-operator reconstruction error <=1e-12;
2. verify native final states/capability are unchanged <=1e-12 where numeric;
3. recompute the SCALE-PAIR-PHASE-22 direct pair-label (6,7) DeltaP.

## Primary question

Is the reported pair-label effect basis invariant?

Let `T_native` be the original-basis mean DeltaP_(6,7).

Let `T_r` be the same label statistic after valid degenerate-subspace rotation r.

Report:
- min, max, median, standard deviation of T_r;
- sign fraction;
- percentile position of T_native;
- fresh pair rank of label (6,7) under each basis where applicable.

## Classification

No arbitrary effect-size threshold.

`PAIR_LABEL_NOT_IDENTIFIABLE` if the valid basis rotations produce both positive and negative values of T_r, or if the target fresh rank spans both top-5% and below-median positions while the underlying operator/native capability remain unchanged.

`PAIR_LABEL_BASIS_STABLE` otherwise.

If operator/native invariance fails numerical tolerance, verdict is `INSUFFICIENT_EVIDENCE`.

## Interpretation boundary

If pair label is not identifiable, prior evidence for pair (6,7) must be reinterpreted as evidence for interaction involving degenerate invariant subspaces, not the individual SVD vectors carrying labels 6 and 7.

The next mechanism test must then be formulated on basis-invariant projectors/subspaces.
