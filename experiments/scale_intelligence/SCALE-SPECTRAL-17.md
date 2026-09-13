# SCALE-SPECTRAL-17 — Task spectrum × interaction operator

Status before canonical execution: PREREGISTERED.

## Question

Does the capability optimum arise where the fixed interaction operator best suppresses task-generated non-global modes relative to the global majority signal?

SCALE-CORRELATION-16 falsified both nominal block width and a single exponential correlation length as general scalar explanations. This protocol moves from one task-length scalar to the full task-state/operator interaction.

## Canonical base

`ac7079c26da8fdbdc655eaf3c609df3ae6bc400e`

## Frozen substrate

Reuse the 63-node line system unchanged:

- interaction scales every integer `4..15`;
- 3 synchronous rounds;
- four message slots `[-2s,-s,+s,+2s]`;
- one scalar state channel;
- self plus four messages divided by 5;
- central scoring nodes `16..46`;
- reflected and self-padded endpoint rules;
- global-majority capability target.

Fresh paired seeds:

`67067, 68068, 69069, 70070, 71071`.

Each task/scale/replicate uses 256 episodes per capability stream.

## Frozen task suite

Two generator families are included so the candidate mechanism must explain both the previously clean segmented regime and the correlation-separated regime.

### A. Segmented generator

Existing `noisy_blocks` generator with blocks:

`7, 10, 13`.

### B. Block-Markov generator

Existing SCALE-CORRELATION-16 generator with:

- nominal block `B ∈ {3, 6}`;
- latent correlation length `L ∈ {8, 11, 14}`.

Total task geometries: 9.

No task parameter is selected after execution.

## Operator-derived primary metric

For each initial state vector `x`:

1. `mu = mean(x)`;
2. `r = x - mu * 1`;
3. let `A_s` be the exact one-round linear update operator for the tested interaction scale and boundary rule;
4. propagate only the centered residual:
   `r3 = A_s^3 r`;
5. on central nodes C=16..46, compute
   `residual_power = mean(r3[C]^2)`;
6. define the bounded target-signal fraction:
   `spectral_target_fraction = mu^2 / (mu^2 + residual_power)`.

Because every update operator satisfies `A_s 1 = 1`, the global mean component is an exact fixed mode. The metric therefore asks how much task-generated non-global structure remains relative to the globally sufficient majority signal after the fixed compute budget.

The metric uses only the initial task state and the known deterministic linear operator. It does not use final node signs, capability scores, nuisance twins, or post-outcome task weighting.

Per scale/replicate score = mean spectral_target_fraction over the exact same initial episodes used by the capability stream.

Capability is unchanged: mean central-node global-majority sign accuracy over the frozen unrotated and rotated streams.

## Frozen peak rule

For both metrics:

1. exact observed argmax over scales 4..15 per replicate/task/boundary;
2. exact ties use arithmetic mean of tied scales;
3. task-level peak = median of five replicate peaks;
4. no smoothing, interpolation, polynomial fit, or threshold retuning.

## Preregistered gates

`NOT_FALSIFIED_BY_DATA` requires all:

1. complete paired coverage, seed pairing and invariant integrity;
2. numerical decomposition check on canonical samples:
   `A_s^3 x = mu*1 + A_s^3(x-mu*1)` within max absolute error `1e-12`;
3. median spectral peak is within 1 scale unit of median capability peak in at least `15/18` boundary×task cells;
4. median spectral peak is within 2 scale units of capability peak in all `18/18` cells;
5. at least `75/90` paired replicate peak pairs are within 2 scale units;
6. Spearman rank correlation between the 18 median spectral-peak locations and the 18 median capability-peak locations is at least `0.80`;
7. within-cell Spearman correlation across the 12 scale-wise mean curves (spectral score vs capability) is at least `0.80` in at least `15/18` cells;
8. for at least `7/9` task geometries, the reflected→self-padded change in spectral median peak predicts the reflected→self-padded capability median-peak change within 1 scale unit.

Any empirical gate failure gives `FALSIFIED_BY_DATA`.
Malformed/incomplete data, invariant drift, or decomposition failure gives `INSUFFICIENT_EVIDENCE`.

## Diagnostics

Record separately:

- segmented vs block-Markov performance;
- spectral peak, capability peak and their delta;
- boundary-induced peak deltas;
- scale-wise spectral/capability curves;
- residual power itself.

Information-efficiency is not part of this protocol.

## Interpretation boundary

A surviving result would support only the bounded mechanism claim that, on this linear toy substrate, capability peak location is predicted by task-weighted suppression of non-global operator modes relative to the preserved global-majority mode.

It would not establish a universal law of intelligence. A surviving result would next need transfer to a different interaction kernel or a nonlinear update rule.

No outcome-dependent retuning is permitted.
