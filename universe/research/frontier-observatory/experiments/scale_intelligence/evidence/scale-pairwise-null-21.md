# SCALE-PAIRWISE-NULL-21 — result

Primary status: `PREDICTIVE_AGAINST_NULL`.

Canonical base: `23710d3b371fcf43dbf12bd4259f513210d07cc7`  
Preregistration: `369ab676b0ea372532ea0c7b44b8ec3d11d206e1`  
Frozen discovery vector: `fb97a4d0850827ea9a7f1bc6de2ae21f863ece7c`

## Why this is different from SCALE-PAIRWISE-20

No absolute pair-effect floor such as `0.006` or `0.004` enters the primary inference.

The primary question is purely predictive:

> Does the full 465-pair discovery ranking contain more information about fresh binary-capability pair interactions than expected under pair-label exchangeability?

## Fresh data

Fresh seeds:

`87087, 88088, 89089, 90090, 91091, 92092, 93093, 94094, 95095, 96096`.

All 465 unordered mode pairs were evaluated with exact 2×2 binary-capability interactions at scales 7 and 13.

## Primary statistic

Spearman correlation between the prospectively frozen discovery vector and fresh pair differential:

`rho = 0.23896583095`.

Deterministic permutation null:

- permutations: `100,000`;
- RNG seed: `210021`;
- null correlations >= observed: `0`;
- +1 corrected one-sided empirical p:
  `0.0000099999`.

At the preregistered single-test alpha=0.05:

`PREDICTIVE_AGAINST_NULL`.

The effect-size magnitude was not gated.

## Secondary frozen top-5 null

Frozen pairs from prior discovery:

`(6,7), (4,6), (3,4), (3,5), (7,8)`.

Fresh pair differentials:

- (6,7): `0.00272020`
- (4,6): `0.00075132`
- (3,4): `0.00189800`
- (3,5): `0.00093403`
- (7,8): `0.00205236`

Sum:

`0.00835591`.

Against 100,000 uniformly sampled random 5-pair subsets:

- RNG seed: `210022`;
- null sets >= frozen set: `1`;
- empirical one-sided p: `0.0000199998`.

No minimum top-5 sum was required.

Fresh ranks of the five frozen pairs:

- (6,7): `1 / 465`
- (7,8): `11 / 465`
- (3,4): `14 / 465`
- (3,5): `40 / 465`
- (4,6): `49 / 465`

The original discovery rank-1 pair (6,7) again ranked #1 on the new fresh dataset.

## Native relevance context

Native self-padded segmented-block-13 scale13-minus-scale7 capability advantage across the 10 fresh replicates:

- 0.02363
- 0.04070
- 0.03446
- 0.02980
- 0.04139
- 0.03056
- 0.03383
- 0.03642
- 0.03950
- 0.03913

Mean:

`0.0349420`.

Bootstrap 95% CI:

`[0.03146, 0.03812]`.

This was reported as context, not used as a materiality gate.

## Integrity

- complete 465-pair coverage;
- 10 fresh replicates;
- max numerical reconstruction error: `8.77e-15`;
- frozen discovery-vector hash:
  `sha256:0c89e1c7d3b39c93abb03ac3a7bbee0d9079afb3c23ec5697b7839e659568132`;
- runner was corrected before canonical rerun to recompute this hash from all decoded 465 float64 values rather than trust the stored hash field;
- rerun statistics were identical.

## Interpretation

This is stronger and cleaner than the absolute-threshold result in SCALE-PAIRWISE-20.

The prospectively derived pair ranking contains statistically detectable out-of-sample information about fresh pairwise capability interactions across the complete pair space.

The result does not depend on deciding beforehand that `0.006` is “large enough.”

It still does not establish that pair (6,7), or the frozen top five, are individually necessary. That requires a direct intervention.

The next test should now return to the causal question with the statistical calibration cleaned up: selectively disrupt pair (6,7) while preserving the remaining modal amplitudes and compare the observed effect with a null distribution of identically constructed pair disruptions.
