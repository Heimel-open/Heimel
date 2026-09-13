# SCALE-BASIS-23 — result

Protocol classification: `PAIR_LABEL_BASIS_STABLE`.

Canonical base: `79efda1eef41948b9a7b1317ada355ceea3b501d`  
Preregistration: `f47dc20d4d03694a047d2ec7e8ad2aceabbe76af`

## Audit trigger

The prior pair label (6,7) sits inside exactly degenerate SVD structure.

Scale 7 singular values:

- mode 6: `0.3319678835621490`
- mode 7: `0.33196788356214885`
- mode 8: `0.33196788356214857`

Scale 13:

- mode 6: `0.6853996558212818`
- modes 7..11: `0.6358212016494861 ... 0.6358212016494855`

Thus:
- scale-7 modes 6/7/8 form one three-dimensional invariant singular subspace;
- scale-13 modes 7/8/9/10/11 form one five-dimensional invariant singular subspace.

Individual SVD vectors inside those blocks are not unique.

## Basis intervention

1,000 deterministic Haar-orthogonal rotations were applied jointly to U and V inside the degenerate blocks.

The transfer operator remained invariant.

Maximum operator reconstruction error:

`1.19e-15`.

Conservative bound on any native centered-state error from the operator difference:

`1.50e-13`.

Both are below the frozen `1e-12` validity tolerance.

## Pair-label statistic under equivalent bases

Original-basis pair (6,7) DeltaP:

`0.00550970`.

Across 1,000 mathematically equivalent SVD bases:

- minimum: `0.00119078`
- maximum: `0.01039567`
- median: `0.00482453`
- standard deviation: `0.00156987`
- positive: `1000/1000`
- negative: `0/1000`
- original basis percentile: `64.8%`

The sign is robust.

The numerical magnitude is not.

The same unchanged operator permits roughly a 9x range in the statistic attached to the literal labels "(6,7)".

## Rank audit

The native basis placed (6,7) at rank #4 / 465.

Only pair labels involving indices 6..11 can change under the audit rotations.

Therefore:

- 300 pair labels are exactly basis-invariant;
- 164 other pair labels can move;
- at the smallest observed rotated target statistic, only 32 of the 300 invariant pairs exceed it;
- even in the worst possible ordering where all 164 affected alternatives exceed it, target rank cannot be worse than #197.

Thus the preregistered "top-5% and below-median" instability criterion cannot occur. Combined with the 1000/1000 positive sign, the frozen protocol classifies the functional sign as basis-stable.

## Correct interpretation

The protocol label `PAIR_LABEL_BASIS_STABLE` must not be read as saying that SVD vector #6 or #7 is a unique physical mechanism.

Exact degeneracy proves they are not uniquely defined.

What survived the audit is narrower and more interesting:

> whichever basis is chosen inside the relevant degenerate subspaces, the pair-label construction continues to expose a positive scale-13-versus-scale-7 interaction signal.

But its amplitude depends substantially on the arbitrary coordinate basis.

Therefore the mechanism should now be reformulated in basis-invariant terms:

- orthogonal projectors onto the degenerate singular subspaces;
- principal angles / canonical correlations between task structure and those subspaces;
- interaction between invariant subspaces, not named singular vectors.

The next experiment should replace "(6,7)" entirely with projector-level interventions.

## Consequence for prior results

SCALE-PAIRWISE-20/21/22 remain evidence that the SVD representation was detecting structured interaction.

They should no longer be interpreted literally as proving that two uniquely identified physical modes numbered 6 and 7 are the mechanism.

The stronger defensible statement is:

> the effect localizes to interaction involving the degenerate mid-spectrum singular subspaces containing those coordinates.

This audit narrows the ontology from basis vectors to invariant subspaces.
