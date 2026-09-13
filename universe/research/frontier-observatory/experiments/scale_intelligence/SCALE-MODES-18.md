# SCALE-MODES-18 — Mode-resolved signed residual test

Status before canonical execution: PREREGISTERED.

## Question

Does capability peak depend on which operator modes survive and whether their local contribution is harmful to the correct decision, rather than on total residual power alone?

SCALE-SPECTRAL-17 showed that total non-global residual power captures most curve shape but fails a strong peak-location claim, dominated by self-padded segmented block 13. This protocol keeps the same task suite and resolves the residual into orthogonal operator modes before aggregating only target-opposing modal contribution.

## Canonical base

`ec8a4cfe20a614e11d98330fbd0c9a66c8963d98`

## Frozen substrate and task suite

Unchanged from SCALE-SPECTRAL-17:

- 63-node line;
- central scoring nodes 16..46;
- reflected and self-padded boundary conditions;
- interaction scales every integer 4..15;
- 3 synchronous rounds;
- four message slots [-2s,-s,+s,+2s];
- one scalar state channel;
- self plus four messages divided by 5;
- global-majority target;
- segmented tasks with blocks 7, 10, 13;
- block-Markov tasks B=3 and B=6 crossed with L=8, 11, 14;
- exact observed-argmax peak rule.

Fresh paired seeds:

`72072, 73073, 74074, 75075, 76076`.

Each task/replicate uses 256 unrotated + 256 rotated capability episodes.

## Frozen mode decomposition

For each boundary condition and interaction scale:

1. let `A_s^3` be the exact three-round linear operator;
2. let `Q = I - 11^T/N` remove the global/DC component;
3. let `P_C` select central nodes 16..46;
4. define residual transfer operator `B_s = P_C A_s^3 Q`;
5. compute the deterministic thin SVD:
   `B_s = U_s Sigma_s V_s^T`.

For an initial episode `x`:

- `mu = mean(x)`;
- target `t = sign(mu)`;
- centered state `r = x - mu*1`;
- mode coefficient `c_j = v_j^T r`;
- central contribution of mode j:
  `y_j = sigma_j c_j u_j`.

The sum over all mode contributions reconstructs the central residual.

## Primary predictor

For each mode contribution, retain only its target-opposing local component:

`h_j = mean_i [min(0, t * y_{j,i})^2]`.

Per episode:

`H = sum_j h_j`.

Define:

`mode_harm_target_fraction = mu^2 / (mu^2 + H)`.

This differs from SCALE-SPECTRAL-17 in two frozen ways:

- residuals are resolved by orthogonal transfer modes;
- only target-opposing contribution of each mode counts as harmful.

The score uses only the initial state, known target and deterministic operator decomposition. It does not use final sign accuracy or capability score.

Per scale/replicate predictor = mean mode_harm_target_fraction over exactly the same episodes used by capability.

## Frozen numerical checks

Before interpretation:

- SVD reconstruction `B_s ≈ U Sigma V^T` max absolute error <= 1e-12;
- modal output reconstruction for canonical episode samples <= 1e-12;
- full state decomposition `A_s^3 x = mu*1 + A_s^3(x-mu*1)` <= 1e-12.

Any failure gives `INSUFFICIENT_EVIDENCE`.

## Frozen peak rule

For predictor and capability:

1. exact observed argmax over scales 4..15 per replicate/task/boundary;
2. exact ties use arithmetic mean of tied scales;
3. task-level peak = median of five replicate peaks;
4. no smoothing, fitting, interpolation or post-outcome threshold change.

## Preregistered gates

`NOT_FALSIFIED_BY_DATA` requires all:

1. complete paired coverage, seed pairing and invariant integrity;
2. all numerical reconstruction checks pass;
3. median predictor peak is within 1 scale unit of capability peak in at least 15/18 boundary×task cells;
4. median predictor peak is within 2 scale units in all 18/18 cells;
5. at least 75/90 paired replicate peak pairs are within 2 scale units;
6. Spearman correlation between the 18 median predictor peaks and 18 capability peaks is >= 0.85;
7. within-cell Spearman correlation between the 12 scale-wise mean predictor and capability curves is >= 0.80 in at least 16/18 cells;
8. for at least 8/9 task geometries, the reflected→self-padded predictor median-peak shift matches the capability median-peak shift within 1 scale unit.

Any empirical gate failure gives `FALSIFIED_BY_DATA`.

## Diagnostics

Record:

- per-mode harmful contribution averaged by cell;
- effective harmful-mode count;
- top-1/top-3 harmful-mode shares;
- segmented vs block-Markov results;
- the previously problematic self-padded segmented block 13 cell separately.

These diagnostics do not alter gates.

## Interpretation boundary

A surviving result would support only the bounded claim that mode identity plus target-opposing sign structure predicts capability peak better than total non-global residual power on this linear toy substrate.

It would not establish a universal mechanism. The next test would require transfer to another interaction kernel or nonlinear update.

No outcome-dependent retuning is permitted.
