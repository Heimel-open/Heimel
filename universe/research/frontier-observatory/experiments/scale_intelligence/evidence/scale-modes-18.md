# SCALE-MODES-18 — result

Status: `FALSIFIED_BY_DATA`.

Canonical base: `ec8a4cfe20a614e11d98330fbd0c9a66c8963d98`  
Preregistration: `05965bda3a9caccbb6977b89858f45c2cb705799`

## Frozen predictor

The residual transfer operator was resolved with the thin SVD:

`B_s = P_C A_s^3 Q = U Sigma V^T`.

For each episode, every modal contribution was target-aligned and only its target-opposing squared local contribution was counted:

`h_j = mean_i[min(0, t*y_ji)^2]`.

The predictor was:

`mode_harm_target_fraction = mu^2 / (mu^2 + sum_j h_j)`.

It used the initial state, target and deterministic operator only. It did not use final sign accuracy.

## Result

Formal verdict: `FALSIFIED_BY_DATA`.

Only the numerical reconstruction gate passed.

Observed:

- median peaks within 1 scale unit: `12/18` (required 15/18);
- all medians within 2: failed;
- paired replicate peaks within 2: `71/90` (required 75/90);
- median peak Spearman: `0.7561` (required >=0.85);
- within-cell curve Spearman >=0.80: `15/18` (required 16/18);
- boundary-delta prediction within 1: `3/9` tasks (required 8/9).

Numerical checks remained clean:

- max SVD/state/modal reconstruction error: `1.52e-14`, below `1e-12`.

## Median peaks

### Reflected

| task | mode-harm predictor | capability | error |
|---|---:|---:|---:|
| seg_b7 | 7 | 7 | 0 |
| seg_b10 | 10 | 10 | 0 |
| seg_b13 | 13 | 13 | 0 |
| markov_b3_l8 | 15 | 11 | 4 |
| markov_b3_l11 | 13 | 13 | 0 |
| markov_b3_l14 | 15 | 12 | 3 |
| markov_b6_l8 | 15 | 12 | 3 |
| markov_b6_l11 | 15 | 13 | 2 |
| markov_b6_l14 | 15 | 13 | 2 |

### Self-padded

| task | mode-harm predictor | capability | error |
|---|---:|---:|---:|
| seg_b7 | 7 | 7 | 0 |
| seg_b10 | 10 | 9 | 1 |
| seg_b13 | 7 | 13 | 6 |
| markov_b3_l8 | 6 | 7 | 1 |
| markov_b3_l11 | 8 | 7 | 1 |
| markov_b3_l14 | 8 | 7 | 1 |
| markov_b6_l8 | 6 | 6 | 0 |
| markov_b6_l11 | 6 | 6 | 0 |
| markov_b6_l14 | 8 | 9 | 1 |

## Dominant exception

Self-padded segmented block 13 remains the strongest counterexample.

At scale 7:

- predictor = `0.5802555`;
- capability = `0.7954133`.

At scale 13:

- predictor = `0.5790379`;
- capability = `0.8270791`.

The mode-harm predictor sees almost no difference, while capability improves materially.

Mode concentration is also similar:

- effective harmful-mode count: `5.26` at scale 7 vs `5.13` at scale 13;
- top-3 harmful share: `0.669` vs `0.680`.

Thus neither total residual power nor independently summed target-opposing modal harm is sufficient.

## Interpretation

The strong mode-resolved independent-harm hypothesis is falsified.

The remaining mechanism is narrower: modal contributions can cancel or reinforce one another at individual nodes. Capability depends on the sign of the combined residual relative to the decision margin, so pairwise/higher-order modal interference can matter even when total harm and per-mode harm are almost unchanged.

The next hard test should therefore measure causal modal interference terms rather than independent modal burdens.

## Validation

- canonical cells: `1080`;
- 512 episodes per task/replicate (256 unrotated + 256 rotated);
- fresh seeds: `72072, 73073, 74074, 75075, 76076`;
- local CPU/vectorized execution: ~`9.81 s`;
- no model/API calls;
- trial digest: `sha256:ba4d1eb8f67ac9000a67fde5490c2cda162612dc0f18860f6fd82e69161995cb`;
- compact result digest: `sha256:a444a526774c2c1de7289832653baa6d5c4a8b431b7686b196885cc3192ef78b`.
