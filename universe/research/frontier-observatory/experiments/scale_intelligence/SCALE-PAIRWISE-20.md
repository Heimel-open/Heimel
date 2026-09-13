# SCALE-PAIRWISE-20 — Phase B confirmatory pair attribution

Status before fresh execution: PREREGISTERED.

Discovery ranking and pair identities were frozen in:
- protocol commit `45c82af95d7bff0b7e3ec247b687396eed9edf92`
- ranking result commit `911186588454b1293d29eba3ae1e634a5f74d4c6`

No fresh seeds were used in Phase A.

## Fixed primary phenomenon

- boundary: self-padded
- task: segmented block 13
- scale contrast: 13 vs 7
- central scoring: nodes 16..46

Fresh confirmatory seeds:

`82082, 83083, 84084, 85085, 86086`.

## Frozen top-5 discovery pairs

`(6,7), (4,6), (3,4), (3,5), (7,8)`.

These are fixed before fresh execution.

## Confirmatory causal pair measurement

For every one of the 465 unordered pairs among the 31 thin-SVD residual modes, and for each fresh replicate at scales 7 and 13:

1. keep all non-pair modes at their native sign;
2. evaluate actual binary central capability for the four sign states:
   `(++), (+-), (-+), (--)`;
3. compute exact factorial pair interaction:
   `J_jk = (C++ + C-- - C+- - C-+)/4`.

This 2×2 contrast cancels the two single-mode main effects and isolates the conditional pair interaction in actual capability.

Define pair differential:

`D_jk = J_jk(scale13) - J_jk(scale7)`.

Positive D means that pairwise interaction contributes more favorably to capability at scale 13 than at scale 7.

## Native phenomenon

For each replicate:

`native_adv = C_native(scale13) - C_native(scale7)`.

## Preregistered gates

The pairwise attribution hypothesis is `NOT_FALSIFIED_BY_DATA` only if all hold:

1. complete coverage of all 465 pairs × 5 fresh replicates, invariant integrity and numerical reconstruction <= 1e-12;
2. fresh native scale13-scale7 advantage mean >= 0.020;
3. native advantage positive in at least 4/5 replicates;
4. sum of the five frozen top-pair differentials, averaged across replicates, >= 0.006;
5. per-replicate top-5 differential sum >= 0.004 in at least 4/5 replicates;
6. at least 4/5 frozen top pairs have positive mean D on fresh data;
7. the mean fresh D of the frozen top-5 pairs is >= the empirical 90th percentile of mean D across all 465 pairs.

If the native phenomenon fails gates 2 or 3, verdict is `INSUFFICIENT_EVIDENCE`.

If native replicates but any pair-attribution gate 4-7 fails, verdict is `FALSIFIED_BY_DATA`.

## Diagnostics

Record:

- fresh rank of each discovery top-5 pair among all 465 pairs;
- top-5 summed D / native advantage as a descriptive pairwise-attribution ratio;
- top 20 fresh pairs;
- pair interaction matrix;
- overlap structure among top pairs.

The attribution ratio is descriptive because higher-order interactions can make pairwise terms non-additive.

## Interpretation boundary

A surviving result would support:

> A small set of mode pairs selected prospectively from a non-outcome margin surrogate carries unusually strong, reproducible capability interaction specifically at scale 13 relative to scale 7.

It would not establish that these five pairs fully explain the phenomenon. Higher-order interactions remain possible.

No outcome-dependent pair substitution, K change or threshold change is permitted.
