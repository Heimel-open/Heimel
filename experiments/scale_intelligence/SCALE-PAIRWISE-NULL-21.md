# SCALE-PAIRWISE-NULL-21 — Null-calibrated predictive replication

Status before fresh execution: PREREGISTERED.

## Why this protocol exists

SCALE-PAIRWISE-20 used several absolute materiality thresholds such as top-5 sum >= 0.006. Those thresholds were frozen before fresh data, but they were design choices rather than quantities derived from the model.

This protocol removes those absolute effect-size gates.

## Fixed question

Does the discovery interaction score carry out-of-sample predictive information about fresh binary-capability pair interactions?

Fixed phenomenon:
- self-padded boundary;
- segmented block 13;
- scale contrast 13 vs 7;
- all 465 unordered pairs among 31 residual modes.

## Discovery vector

Discovery scores are recomputed only from prior SCALE-INTERFERENCE-19 seeds:

`77077, 78078, 79079, 80080, 81081`.

The score is exactly the frozen SCALE-PAIRWISE-20 smooth-margin interaction differential:

`D_discovery(j,k) = I13(j,k) - I7(j,k)`.

All 465 values are frozen in a repository artifact before fresh execution.

No fresh outcome is used to construct or transform this vector.

## Fresh confirmatory data

Fresh seeds:

`87087, 88088, 89089, 90090, 91091, 92092, 93093, 94094, 95095, 96096`.

For every fresh seed and every one of the 465 pairs, compute the exact binary-capability 2x2 factorial interaction at scales 7 and 13:

`J_jk = (C++ + C-- - C+- - C-+)/4`.

Fresh pair differential:

`D_fresh(j,k) = mean_r[J13_r(j,k)-J7_r(j,k)]`.

## Primary statistic

`T = Spearman(D_discovery, D_fresh)` across all 465 pairs.

This uses the complete ranked prediction rather than an arbitrary top-k effect threshold.

## Primary null

`H0`: pair identity in the discovery vector is exchangeable with respect to fresh pair interaction.

Generate exactly 100,000 deterministic permutations of the fresh 465-vector using NumPy PCG64 seed:

`210021`.

For each permutation compute Spearman correlation with the fixed discovery vector.

One-sided empirical p-value:

`p = (1 + count(T_null >= T_observed)) / 100001`.

The inferential decision uses the conventional single-test level `alpha = 0.05`.

- `PREDICTIVE_AGAINST_NULL` if p <= 0.05 and T_observed > 0.
- `NOT_PREDICTIVE_AGAINST_NULL` otherwise.

No minimum absolute rho is imposed.

## Secondary null-calibrated diagnostics

These do not alter the primary outcome.

1. Frozen prior top-5 set:
   `(6,7), (4,6), (3,4), (3,5), (7,8)`.

   Statistic:
   sum of fresh D across those five pairs.

   Null:
   100,000 deterministic uniformly sampled 5-pair subsets without replacement, RNG seed `210022`.

   Report empirical percentile and one-sided p-value. No effect-size threshold.

2. Discovery rank-1 pair `(6,7)`:
   report its fresh rank among all 465 and exact empirical rank percentile.

3. Native scale13-scale7 capability advantage:
   report mean, replicate values, and bootstrap 95% CI. This is relevance context, not a materiality gate.

If mean native advantage <= 0, the pair-prediction test is still mathematically valid, but interpretation must not claim explanation of a reproduced scale13 advantage.

## Integrity gates

Only validity failures can yield `INSUFFICIENT_EVIDENCE`:

- incomplete 465-pair coverage;
- seed mismatch;
- duplicate pairs;
- numerical reconstruction error > 1e-12;
- discovery-vector hash mismatch;
- permutation count or RNG seed mismatch.

No observed effect-size magnitude can yield `INSUFFICIENT_EVIDENCE`.

## Interpretation boundary

A positive primary result means only that the prospectively frozen discovery ranking contains statistically detectable information about fresh pairwise capability interactions on this fixed toy substrate.

It does not mean all pairs are causal, nor that the top-5 explain a fixed fraction of capability.

No outcome-dependent retuning is permitted.
