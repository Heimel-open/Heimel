# SCALE-PAIRWISE-20 — confirmatory result

Status: `NOT_FALSIFIED_BY_DATA`.

Canonical base: `f82df8d651f8b486deaaeb776b80caad6aaa17b3`  
Discovery freeze: `45c82af95d7bff0b7e3ec247b687396eed9edf92`  
Discovery pair list: `911186588454b1293d29eba3ae1e634a5f74d4c6`  
Confirmatory preregistration: `9e08a6e4dc0c0b32e57b18593a3e19c0f3bd4b14`

Fresh seeds:

`82082, 83083, 84084, 85085, 86086`.

## Native phenomenon

Self-padded segmented block 13, scale13 minus scale7 capability:

- `+0.04284`
- `+0.03276`
- `+0.03409`
- `+0.03270`
- `+0.03238`

Mean:

`+0.03495`.

Positive in `5/5` fresh replicates.

## Frozen discovery pairs on fresh binary capability

The confirmatory measurement used the exact 2×2 factorial capability interaction

`J_jk = (C++ + C-- - C+- - C-+)/4`

with all non-pair modes held native.

Fresh differential:

`D_jk = J_jk(scale13) - J_jk(scale7)`.

| discovery rank | pair | fresh mean D | fresh rank / 465 |
|---:|---|---:|---:|
| 1 | (6,7) | 0.002974 | 1 |
| 2 | (4,6) | 0.002000 | 12 |
| 3 | (3,4) | 0.001484 | 25 |
| 4 | (3,5) | 0.000617 | 61 |
| 5 | (7,8) | 0.001660 | 20 |

All five have positive fresh mean interaction differential.

Top-5 summed differential:

`0.0087355` (required >= `0.006`).

Per fresh replicate top-5 summed D:

- `0.009025`
- `0.008474`
- `0.008033`
- `0.008647`
- `0.009498`

All `5/5` exceed the preregistered `0.004` replicate floor.

Mean D across the frozen top five:

`0.0017471`.

Empirical 90th percentile across all 465 fresh pair means:

`0.0008058`.

Thus the prospectively selected set is strongly enriched above the fresh all-pair background.

## Descriptive attribution ratio

`top5 summed D / native advantage = 0.2499`.

This is approximately one quarter of the observed native scale13-over-scale7 advantage in pairwise ANOVA units.

It must not be interpreted as exact explained variance because pairwise and higher-order terms need not add linearly.

## Fresh top pairs

The strongest fresh pair was the discovery #1 pair:

`(6,7): D = 0.002974`.

Other high fresh pairs included:

- (2,13): 0.002640
- (0,2): 0.002630
- (2,4): 0.002561
- (8,10): 0.002489
- (1,4): 0.002432
- (9,10): 0.002325
- (6,8): 0.002319
- (8,9): 0.002284
- (10,11): 0.002133

This confirms that the five discovery pairs are not the complete interaction structure. They are a prospectively enriched subset.

## Gates

All preregistered confirmatory gates passed:

- full 465-pair coverage × 5 fresh replicates;
- numerical reconstruction <= 1e-12;
- native advantage >=0.020;
- native positive >=4/5;
- frozen top-5 summed D >=0.006;
- replicate top-5 sum >=0.004 in >=4/5;
- >=4/5 frozen pairs positive;
- frozen top-5 mean D >= empirical fresh 90th percentile.

## Interpretation

SCALE-PAIRWISE-20 moves the mechanism one level deeper.

The causal phase-scrambling result from SCALE-INTERFERENCE-19 is not only a diffuse many-mode effect. A small set of mode pairs selected prospectively from a non-outcome margin surrogate carries unusually strong and reproducible pairwise capability interaction at scale 13 relative to scale 7.

The strongest discovery pair, modes 6 and 7, independently replicated as the strongest of all 465 fresh pair interactions.

However, the fresh top-20 also contains several pairs not selected in discovery. Higher-order and broader pair structure remain open.

The next hard test should intervene directly on the strongest pair(s), especially (6,7), and determine whether their native relative phase is necessary, then test whether adding the next-ranked pairs produces cumulative recovery/collapse.

## Validation

- 465 unordered mode pairs;
- 5 fresh replicates;
- 2 scales;
- exact four-state factorial capability per pair;
- 512 episodes per replicate;
- no model/API calls;
- trial digest: `sha256:c60889e53c8ddf4d993ca44c93898bfbcd98d8aab220d66b18cdf16f2cc29ebb`.
