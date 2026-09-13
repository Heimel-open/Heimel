# SCALE-COPULA-28 — Causal destruction of relational organization

Status before confirmatory execution: PREREGISTERED.

## Question

Does the scale-13 capability advantage depend causally on the joint organization among invariant spectral-block contributions, rather than on the marginal contribution distribution of each block?

## Canonical base

`b2109e4f7298134a7c5ca35f4aeb6dbbaf17dd6e`

## Fixed invariant decomposition

Use the same 12 scale-13 operator-defined maximal singular-value projectors from SCALE-BLOCKCROSS-27:

0. {0,1,2,3}
1. {4}
2. {5}
3. {6}
4. {7,8,9,10,11}
5. {12,13,14,15,16}
6. {17}
7. {18,19,20,21,22}
8. {23}
9. {24,25,26,27}
10. {28,29}
11. {30}

Add a 13th invariant component:

`P_12 = Q - sum(P_0..P_11)`

where Q is the centered-input projector.

Thus the 13 projectors form a complete orthogonal partition of the 62-dimensional centered input space.

For scale s and centered residual r:

`y_b = B_s P_b r`.

The native centered output is exactly:

`sum_b y_b = B_s r`.

No individual SVD basis vector is used.

## Stable capability

Use the SCALE-BLOCKCROSS-27 score:

- target-aligned margin > +1e-12 -> 1
- margin < -1e-12 -> 0
- |margin| <=1e-12 -> 0.5

## Fresh confirmatory seeds

`187187,188188,189189,190190,191191,192192,193193,194194,195195,196196,197197,198198,199199,200200,201201,202202,203203,204204,205205,206206`.

Exactly 20 fresh replicates.

All seeds used in prior scale experiments remain excluded.

## Conditional copula intervention

Within each replicate and scale, partition the 512 episodes by exact signed initial mean `mu`.

For every component b, retain each 31-dimensional output contribution vector `y_b` exactly.

### Coupled permutation control

Within each exact-mu stratum, apply the same permutation to every one of the 13 components.

This preserves the complete joint block organization; it only relabels whole centered-output vectors among episodes with identical DC contribution and target.

Therefore pooled stable capability must be exactly unchanged apart from numerical tolerance.

### Independent block permutation

Within each exact-mu stratum, independently permute the 13 component vectors.

This preserves, exactly within each replicate/scale/mu stratum:

- every component's multiset of 31D contribution vectors;
- every component's amplitude distribution;
- every component's spatial pattern distribution;
- every component's relationship to the exact DC state mu;
- episode count and target distribution.

It destroys only the empirical joint dependence/copula among components.

Singleton strata remain unchanged.

## Scramble ensemble

Use exactly 256 deterministic scramble draws per replicate and scale.

For draw q:
- coupled-control RNG seed is a SHA-256-derived deterministic seed from
  `SCALE-COPULA-28|coupled|replicate_seed|scale|q`;
- independent component permutations derive separate SHA-256 seeds from
  `SCALE-COPULA-28|independent|replicate_seed|scale|q|component`.

No outcome-dependent draw selection.

## Primary quantity

For replicate r:

`A_native_r = C_native_13 - C_native_7`.

Let `C_independent_s,r` be mean capability across the 256 independent copula scrambles at scale s.

`A_scrambled_r = C_independent_13,r - C_independent_7,r`.

Define relational collapse:

`K_r = A_native_r - A_scrambled_r`.

Positive K means destroying cross-block organization reduces the scale-13-over-scale-7 capability advantage while preserving block marginals.

## Primary exact inference

Observed statistic:

`T = mean(K_r)/(sd(K_r)/sqrt(20))`.

Enumerate all `2^20=1,048,576` paired sign flips of K.

One-sided exact p:

`p = count(T_null >= T_observed)/2^20`.

No absolute collapse threshold is imposed.

Classification:

- `RELATIONAL_ORGANIZATION_CAUSAL` if mean(K)>0 and p<=0.05;
- `RELATIONAL_ORGANIZATION_NOT_DETECTED` otherwise.

Alpha=0.05 is the only inferential cutoff.

## Integrity gates

Only validity failures yield `INSUFFICIENT_EVIDENCE`:

1. 13-projector completeness/orthogonality error >1e-12.
2. Native decomposition error >1e-12.
3. Any independent scramble changes a component's exact within-stratum multiset checksum.
4. Coupled-control capability differs from native by >1e-12.
5. Fewer than 20 fresh replicates or not exactly 256 scramble draws per scale/replicate.
6. Exact sign-pattern count !=1,048,576.

## Diagnostics

Report without changing primary classification:

- native advantage and bootstrap 95% CI;
- independently scrambled advantage and bootstrap 95% CI;
- collapse K and bootstrap 95% CI;
- scale-specific native-to-scrambled capability changes;
- fraction of scramble draws with scale13 advantage below native;
- distribution of stratum sizes and fraction of episodes in non-singleton strata;
- per-component conditional covariance destruction:
  mean absolute off-diagonal correlation of component energies before and after scrambling;
- coupled-control invariance.

## Interpretation boundary

A positive result supports:

> the scale-13 capability advantage depends causally on the joint organization among invariant component contributions, because destroying only their dependence structure while preserving each conditional marginal reduces the advantage.

It does not identify which higher-order relation is necessary, nor establish a universal law.

No post-outcome threshold, block selection, or scramble selection is permitted.
