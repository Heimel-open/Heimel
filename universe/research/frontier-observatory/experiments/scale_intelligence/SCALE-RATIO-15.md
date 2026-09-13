# SCALE-RATIO-15 — Held-out test of task-scale / interaction-scale matching

Status before canonical execution: PREREGISTERED.

## Question

Is the stable capability optimum better described by a dimensionless matching relation between task spatial correlation length and interaction scale, rather than by the information-efficiency optimum?

Prior runs used task blocks 5, 9 and 13. This protocol uses only held-out block sizes.

## Canonical base

`01e598bbd5c42dcf710cc10eeb2ee5ca23449677`

## Frozen design

Reuse the SCALE-BOUNDARY-DYNAMICS-13 substrate and scoring machinery unchanged:

- 63-node line;
- central scoring nodes `16..46`;
- reflected and self-padded boundary conditions;
- interaction scales every integer `4..15`;
- 3 synchronous rounds;
- four message slots `[-2s,-s,+s,+2s]`;
- scalar state and `/5` update;
- same task generator, noise rate, global-majority target and independent capability streams;
- same exact observed argmax rule, with arithmetic mean for exact ties and median of five replicate peak locations.

Held-out task blocks: `6, 8, 10, 12, 14`.

Fresh paired seeds: `57057, 58058, 59059, 60060, 61061`.

The same generated episodes are evolved under both boundary conditions.

## Primary hypothesis

For capability, the operating optimum tracks task correlation length:

`interaction_scale_peak / task_block ≈ 1`.

## Preregistered gates

For each boundary condition independently:

1. complete paired coverage and invariant integrity;
2. median capability peaks are strictly increasing across blocks 6 < 8 < 10 < 12 < 14;
3. for every held-out block, `|median_peak - task_block| <= 1` scale unit;
4. median absolute error across the five blocks is <= 1 scale unit;
5. for every held-out block, at least 4/5 replicate peak locations are within 2 scale units of the task block.

Boundary robustness additionally requires:

6. for at least 4/5 held-out blocks, reflected and self-padded median capability peaks differ by <= 1 scale unit.

`NOT_FALSIFIED_BY_DATA` requires all six gates.

Any empirical gate failure gives `FALSIFIED_BY_DATA`. Malformed data, incomplete pairing or invariant drift gives `INSUFFICIENT_EVIDENCE`.

## Diagnostics

Record information-efficiency peaks under both boundary conditions, but they are not part of the primary gates. Their purpose is to test whether capability-scale matching survives even when efficiency peaks do not track the same ratio.

Also record the normalized ratio `peak/task_block` for every block and condition.

## Interpretation boundary

A surviving result would support only the bounded claim that, on this toy substrate, capability optimum tracks the task's spatial correlation scale across held-out geometries and two endpoint rules.

It would not establish a universal law of intelligence or prove that literal one-hop matching is the underlying mechanism. The next intervention would need to separate task correlation length from block size itself.

No outcome-dependent retuning is permitted.
