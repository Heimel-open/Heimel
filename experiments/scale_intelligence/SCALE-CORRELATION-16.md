# SCALE-CORRELATION-16 — Correlation length vs nominal block size

Status before canonical execution: PREREGISTERED.

## Question

Does capability peak track the task's actual spatial correlation length when that correlation length is explicitly separated from nominal block size?

SCALE-RATIO-15 showed capability_peak ≈ task_block on held-out block sizes. This protocol breaks that identity.

## Canonical base

`00ef323fe1e712ea3e139cc9c39b0224f2e9c8e2`

## Frozen task generator

The task is a block-Markov spatial field.

For nominal block size `B` and latent correlation length `L`:

1. partition the 63-node field into nominal blocks of width `B`;
2. draw the first latent block sign uniformly from {-1,+1};
3. adjacent latent block signs follow a stationary symmetric two-state Markov process with
   `rho = exp(-B/L)`;
4. therefore `P(next = current) = (1 + rho)/2`;
5. map each latent block sign to its nodes;
6. independently flip each node sign with the existing `NOISE_P = 0.10`;
7. force a non-zero global majority using the existing rule.

For the latent block process, the designed spatial correlation at block-boundary distance `d` is
`corr(d) = exp(-d/L)`.
Thus `L` is the preregistered latent correlation length, while `B` is only the nominal discretization scale.

Random rotation is retained for the independent transfer/capability stream.

## Frozen factorial intervention

Nominal block sizes:

`B = {3, 6}`

Latent correlation lengths:

`L = {8, 11, 14}`

This yields six task conditions in which `B` and `L` are not equal.

Interaction scales:

`4..15` inclusive.

Boundary conditions:

- `reflected`;
- `self_padded`.

Central scoring remains nodes `16..46`.

Fresh paired seeds:

`62062, 63063, 64064, 65065, 66066`.

Each cell uses 256 episodes per probe stream.

The same generated episode is evolved under both boundary conditions.

## Frozen substrate and compute

Unchanged from SCALE-RATIO-15:

- 63 nodes;
- 3 synchronous rounds;
- four message slots [-2s,-s,+s,+2s];
- one scalar state channel;
- self plus four messages divided by 5;
- same reflected and self-padded address rules;
- same global-majority capability score;
- same exact observed-argmax peak rule with arithmetic mean for exact ties and median across five replicates.

Information-efficiency is recorded only as a diagnostic and does not enter primary gates.

## Primary hypothesis

Capability optimum follows latent task correlation length, not nominal block width.

Formally, for both boundary conditions:

`capability_peak ≈ L`

and changing `B` from 3 to 6 at fixed `L` should not materially move the peak.

## Preregistered gates

`NOT_FALSIFIED_BY_DATA` requires all:

1. complete paired coverage, seed pairing and invariant integrity;
2. for each boundary condition and each nominal block size separately, median capability peaks are strictly ordered as `L=8 < L=11 < L=14`;
3. for every one of the 12 boundary × B × L cells, `|median_peak - L| <= 2`;
4. for every boundary × L pair, the two nominal-block median peaks differ by <= 1 scale unit;
5. for every boundary × B × L cell, at least 4/5 replicate peak locations are within 2 scale units of `L`;
6. for at least 10/12 cells, the capability peak is at least 2 scale units closer to `L` than to nominal `B`:
   `|peak-L| + 2 <= |peak-B|`;
7. reflected vs self-padded median capability peaks differ by <= 1 in at least 5/6 B×L task cells.

Any empirical gate failure gives `FALSIFIED_BY_DATA`.
Malformed/incomplete data or invariant drift gives `INSUFFICIENT_EVIDENCE`.

## Generator verification

Before interpreting capability:

- record the configured `rho = exp(-B/L)`;
- estimate adjacent latent-block sign correlation across the canonical episodes;
- convert it back to `L_hat = -B/log(rho_hat)` when 0 < rho_hat < 1.

This is diagnostic, not an outcome gate, because finite 63-node samples can make the estimate noisy. It exists to verify that the implemented generator separates B from L in the intended direction.

## Interpretation boundary

A surviving result would support only the bounded claim that on this toy substrate, capability peak tracks a preregistered latent spatial correlation length when nominal block width is varied independently.

It would not establish that correlation length is the universal mechanism. The next test would need to vary temporal or relational correlation scale, or change the interaction kernel itself.

No outcome-dependent retuning is permitted.
