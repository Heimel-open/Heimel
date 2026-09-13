# SCALE-INTERFERENCE-19 — Causal modal phase/sign scrambling

Status before canonical execution: PREREGISTERED.

## Question

Does the relative sign/phase arrangement between residual transfer modes causally explain the self-padded segmented-block-13 capability optimum that survived SCALE-SPECTRAL-17 and SCALE-MODES-18?

The prior failure is fixed before this run:

- boundary: self-padded;
- task: segmented block 13;
- contrast scales: 7 vs 13.

SCALE-MODES-18 found nearly identical independent modal-harm predictor values at these scales while capability was materially higher at scale 13.

## Canonical base

`9210f5871c6040d4158112f95a2ed5ebae4dbcef`

## Frozen substrate

Unchanged:

- 63-node line;
- central scoring nodes 16..46;
- reflected and self-padded boundary rules;
- scales 4..15;
- 3 synchronous rounds;
- four message slots [-2s,-s,+s,+2s];
- scalar state;
- /5 update;
- global-majority target;
- same nine task geometries as SCALE-MODES-18.

Fresh paired seeds:

`77077, 78078, 79079, 80080, 81081`.

Each task/replicate uses 256 unrotated + 256 rotated episodes.

## Frozen modal decomposition

Reuse SCALE-MODES-18 exactly.

For each boundary condition and scale:

`B_s = P_C A_s^3 Q = U Sigma V^T`.

For each centered task state `r`:

`c = V^T r`.

Native central residual:

`y = U Sigma c`.

## Causal intervention

For each episode, generate 16 deterministic independent Rademacher masks

`epsilon_j ∈ {-1,+1}`

from a seed derived only from protocol seed, task id, scale, boundary condition, episode index and scramble index.

Scrambled residual:

`y^(q) = U Sigma (epsilon^(q) ⊙ c)`.

The global/DC component `mu` is unchanged.

This intervention preserves for every episode and scramble:

- every singular value;
- every absolute modal coefficient `|c_j|`;
- every per-mode L2 energy `sigma_j^2 c_j^2`;
- total central residual L2 power, up to numerical tolerance.

It changes only the relative signs/phases among modal contributions and therefore their local cancellation/reinforcement pattern.

Scrambled capability is computed from

`mu + y^(q)`

using the unchanged central-node global-majority score.

Per trial, `scrambled_capability` is the mean across 16 scrambles.

## Primary endpoint

Fixed cell:

`self_padded / seg_b13 / scale 13 vs scale 7`.

For replicate r:

- `native_adv_r = native_capability_13 - native_capability_7`;
- `scrambled_adv_r = scrambled_capability_13 - scrambled_capability_7`;
- `collapse_r = native_adv_r - scrambled_adv_r`.

## Preregistered gates

`NOT_FALSIFIED_BY_DATA` requires all:

1. complete paired coverage, seed pairing and invariant integrity;
2. SVD/state/modal reconstruction error <= 1e-12;
3. modal-energy preservation under all scrambles: max absolute central residual L2-power error <= 1e-12;
4. fresh native replication: aggregate self-padded seg_b13 capability advantage scale13-scale7 >= 0.020;
5. native advantage is positive in at least 4/5 fresh replicates;
6. scrambled aggregate scale13-scale7 advantage has absolute value <= 0.010;
7. aggregate collapse `native_adv - scrambled_adv >= 0.015`;
8. collapse >= 0.010 in at least 4/5 paired replicates;
9. specificity control: the scale-13 scrambling drop for self-padded seg_b13 exceeds the mean absolute scrambling effect at the independently fixed neighboring control peaks self-padded seg_b7/scale7 and seg_b10/scale9 by >= 0.008.

If the fresh native scale13 advantage fails to reproduce, verdict is `INSUFFICIENT_EVIDENCE`: the fixed phenomenon to explain was absent.

If the phenomenon reproduces but any causal-collapse gate fails, verdict is `FALSIFIED_BY_DATA`.

## Secondary diagnostics

Across all 18 boundary×task cells and scales 4..15, record:

- native capability;
- mean scrambled capability;
- absolute scrambling effect;
- native and scrambled peak locations;
- peak movement;
- phase sensitivity by cell.

These are diagnostic only and do not rescue the primary endpoint.

## Interpretation boundary

A surviving result would support:

> On this fixed linear toy substrate, the self-padded segmented-block-13 scale-13 capability advantage depends causally on the native relative sign/phase arrangement among residual transfer modes, despite unchanged modal amplitudes and total residual energy.

It would establish interference/cancellation as a necessary ingredient for this counterexample, but would not yet identify which mode pairs are responsible. Pairwise attribution would be the next experiment.

No outcome-dependent retuning is permitted.
