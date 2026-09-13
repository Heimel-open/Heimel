# SCALE-SPECTRAL-17 — result

Status: `FALSIFIED_BY_DATA`.

Canonical base: `ac7079c26da8fdbdc655eaf3c609df3ae6bc400e`  
Preregistration: `f73ccd1beafb5946653766fae8c96c5f70c44f1f`

## Frozen mechanism test

The preregistered predictor used only:

- the initial task state;
- the exact deterministic linear interaction operator;
- the preserved global-mean mode;
- task-weighted residual non-global power after three rounds.

Per episode:

`spectral_target_fraction = mu^2 / (mu^2 + central_residual_power)`.

No final node signs, capability scores, nuisance twins, or post-outcome task weighting entered the predictor.

Task suite:

- segmented blocks 7, 10, 13;
- block-Markov B=3 and B=6, each with L=8, 11, 14;
- reflected and self-padded boundary rules;
- scales 4..15;
- five fresh seeds.

## Result

Five of seven empirical gates passed.

Passed:

- operator decomposition error <= 1e-12; observed max `8.88e-16`;
- median spectral/capability peaks within 1 scale unit in `16/18` cells, required 15/18;
- median peak Spearman = `0.8082`, required >=0.80;
- within-cell curve Spearman >=0.80 in `18/18` cells, required 15/18;
- boundary-induced peak-delta prediction within 1 scale unit for `7/9` task geometries, required 7/9.

Failed:

- all 18 median peaks within 2 scale units;
- paired replicate peaks within 2 scale units: observed `74/90`, required 75/90.

The largest failure is highly localized:

- self-padded segmented block 13:
  spectral median peak = `7`;
  capability median peak = `13`;
  absolute peak error = `6`.

## Median peaks

### Reflected

| task | spectral | capability | error |
|---|---:|---:|---:|
| seg_b7 | 7 | 7 | 0 |
| seg_b10 | 10 | 10 | 0 |
| seg_b13 | 13 | 13 | 0 |
| markov_b3_l8 | 13 | 12 | 1 |
| markov_b3_l11 | 15 | 14 | 1 |
| markov_b3_l14 | 15 | 14 | 1 |
| markov_b6_l8 | 13 | 12 | 1 |
| markov_b6_l11 | 13 | 13 | 0 |
| markov_b6_l14 | 15 | 14 | 1 |

### Self-padded

| task | spectral | capability | error |
|---|---:|---:|---:|
| seg_b7 | 7 | 7 | 0 |
| seg_b10 | 10 | 9 | 1 |
| seg_b13 | 7 | 13 | 6 |
| markov_b3_l8 | 8 | 7 | 1 |
| markov_b3_l11 | 8 | 6 | 2 |
| markov_b3_l14 | 8 | 7 | 1 |
| markov_b6_l8 | 6 | 6 | 0 |
| markov_b6_l11 | 7 | 7 | 0 |
| markov_b6_l14 | 8 | 9 | 1 |

## Curve-level relation

Despite the failed peak claim, the scale-wise spectral score and capability curves are strongly rank-correlated in every tested cell.

Range of within-cell Spearman correlations:

- reflected: approximately `0.909–0.986`;
- self-padded: approximately `0.811–0.979`.

All `18/18` exceed the preregistered `0.80` floor.

This means the operator-weighted target/residual metric captures substantial shape information, but it is not sufficient to locate every capability maximum.

## Boundary-delta diagnostic

For 7/9 task geometries, the reflected→self-padded spectral peak shift predicted the capability peak shift within one scale unit.

The two failures were:

- segmented block 13: spectral shift `-6`, capability shift `0`;
- Markov B6/L14: spectral shift `-7`, capability shift `-5`.

Again, segmented block 13 is the dominant exception.

## Interpretation

The strong version is falsified:

> capability peak location is not fully determined by suppression of non-global residual power relative to the preserved global-mean mode.

But this candidate is materially closer than the prior scalar explanations. It predicts most median peaks, all curve directions, and most boundary-induced shifts across two task families.

The surviving uncertainty is now narrow: capability can remain high at a scale where global-mean-vs-residual power is no longer maximal. That implies the missing quantity is likely not total residual power, but which residual modes remain and how their signs align with the decision boundary.

The next test should therefore resolve residual energy by mode/eigenvector class rather than collapse all non-global modes into one RMS number.

## Validation

- canonical trial cells: `1080`;
- 256 episodes per capability stream;
- fresh seeds: `67067, 68068, 69069, 70070, 71071`;
- vectorized semantic mirror execution: ~`1.09 s`;
- scalar/vector parity max absolute error: `4.44e-16`;
- operator decomposition max error: `8.88e-16`;
- trial digest: `sha256:efc1a46c88e04455e65dec900c915ea033d7fb05ec0ee881bffafdb6e463bc0a`;
- compact result digest: `sha256:c4c6326f56288b15a01108b8264f47c0c1ff34431c7affa91840bcfd308da0f8`.
