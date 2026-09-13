# SCALE-COPULA-28 — result

Status: `RELATIONAL_ORGANIZATION_CAUSAL`.

Canonical base: `b2109e4f7298134a7c5ca35f4aeb6dbbaf17dd6e`  
Preregistration: `0cbc1dd30d4d70e85875a52481b71b4d9b7b5e2a`

## Causal intervention

The centered system was decomposed into a complete invariant 13-component partition:

- the 12 maximal scale-13 spectral-block projectors from SCALE-BLOCKCROSS-27;
- the orthogonal centered-space complement.

For each episode and scale, every component contribution was a full 31-dimensional output vector:

`y_b = B_s P_b r`.

The intervention did not alter the set of contribution vectors carried by any component.

Within each replicate, scale and exact signed initial mean / DC state:

- coupled control: all 13 components received the same episode permutation;
- independent scramble: each component received an independent permutation.

Therefore the independent intervention preserved every component's conditional marginal multiset and its exact DC stratum while destroying only the empirical joint dependence / copula among components.

Exactly 256 deterministic scramble draws were used per scale and replicate.

Fresh seeds:

`187187..206206`, 20 independent replicates.

## Integrity

All frozen integrity gates passed.

- complete 13-projector partition error: `6.49e-15`;
- maximum native decomposition error: `2.89e-15`;
- maximum coupled-control capability error: `0.0`;
- all conditional multiset checks: PASS.

The multiset check is an exact source-index bijection within each stratum. Because component vectors are gathered only through those bijections, the vector multisets are preserved exactly.

Mean fraction of episodes belonging to non-singleton exact-DC strata:

`0.98867`.

Thus almost all episodes were eligible for actual relational scrambling.

## Native advantage

Stable native capability:

- scale 7: `0.8002709`;
- scale 13: `0.8338710`.

Native scale13-minus-scale7 advantage:

`+0.0336001`.

Bootstrap 95% CI:

`[0.0319682, 0.0351563]`.

## Independently scrambled advantage

Mean capability after conditional independent block scrambling:

- scale 7: `0.7990928`;
- scale 13: `0.8211059`.

Scrambled scale13-minus-scale7 advantage:

`+0.0220131`.

Bootstrap 95% CI:

`[0.0209952, 0.0231466]`.

The intervention therefore changed scale 7 capability by only:

`-0.0011781`

but changed scale 13 capability by:

`-0.0127651`.

## Relational collapse

Preregistered replicate quantity:

`K = A_native - A_scrambled`.

Mean:

`+0.01158695`.

Bootstrap 95% CI:

`[0.0104244, 0.0126941]`.

Every one of the 20 fresh replicate collapses was positive:

`20/20`.

Replicate collapse values:

- 0.014499
- 0.010210
- 0.011467
- 0.009577
- 0.013994
- 0.015175
- 0.012718
- 0.015899
- 0.009598
- 0.014125
- 0.011076
- 0.012427
- 0.009205
- 0.010754
- 0.005439
- 0.011379
- 0.012424
- 0.011512
- 0.013151
- 0.007113

Observed studentized statistic:

`T = 19.6801`.

The exact paired sign-flip null enumerated all:

`2^20 = 1,048,576`

orientations.

Null patterns with `T >= T_observed`:

`1`.

Exact one-sided p:

`p = 1 / 1,048,576 = 9.5367e-7`.

No absolute collapse threshold entered the inference.

Primary status:

`RELATIONAL_ORGANIZATION_CAUSAL`.

## Scramble-distribution diagnostic

Across all `20 x 256 = 5,120` independent paired scramble draws:

`5,094 / 5,120 = 99.492%`

produced a scale13 advantage below the native advantage for that replicate.

## Dependence diagnostic

Mean absolute off-diagonal correlation among component output energies:

Native:
- scale 7: `0.07944`
- scale 13: `0.08562`

After independent conditional scrambling:
- scale 7: `0.04052`
- scale 13: `0.04013`

Thus the intervention materially reduced cross-component dependence while retaining each component's conditional marginal values.

## Interpretation

This is the first direct intervention in the scale chain that preserves the component marginals and selectively destroys their organization.

The result supports:

> the scale-13 capability advantage depends causally on the joint organization among invariant component contributions.

The important asymmetry is scale-specific. The same marginal-preserving relational destruction barely changes scale 7 but removes about `0.01159` absolute capability advantage from scale 13.

Descriptively, the collapse is about `34.5%` of the native scale13-over-scale7 advantage. This is not an exact "fraction explained": the remaining advantage and nonlinear interactions are not additive decompositions.

The scale13 advantage does not disappear entirely. Therefore relational organization is a causal contributor, not yet demonstrated to be the sole mechanism.

Combined with SCALE-BLOCKCROSS-27, the evidence now has both directions:

1. observational/interventional localization: operating scale reorganizes a broad network of invariant block relations;
2. direct destruction test: breaking that joint organization while preserving block marginals reduces the capability advantage.

The next question is whether the remaining ~2.20 percentage-point advantage is carried by marginal/operator effects or by higher-order relational structure preserved by the conditional scramble.

Trial digest:

`sha256:84adb931b4462e1d4e61475095a4b7c8a0cbc1ee4098c21623be72c2c583663e`.
