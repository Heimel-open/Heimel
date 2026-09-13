# SCALE-BOUNDARY-12 — Boundary-excluded scoring on reflected line

Status before canonical execution: PREREGISTERED.

## Question

Did SCALE-TOPOLOGY-11 fail because endpoint/boundary nodes dominated peak localization, rather than because the task-geometry-to-operating-scale relationship disappeared throughout the reflected-line substrate?

## Canonical base

`6fce414ddff6e503d8c7ccdccd560eba75b63b48`

## Frozen substrate

Reuse SCALE-TOPOLOGY-11 unchanged:

- 63-node reflected line;
- reflected address resolution at endpoints 0 and 62;
- four message slots `[-2s,-s,+s,+2s]`;
- 3 synchronous rounds;
- scalar state;
- identical mean-message update and /5 normalizer;
- task blocks `5, 9, 13`;
- interaction scales every integer `4..15`;
- same segmented generator, nuisance permutation, noise rate and global-majority target.

No state-transition, topology, task, scale-grid, or compute parameter changes in this protocol.

Fresh paired seeds: `42042, 43043, 44044, 45045, 46046`.

## Frozen scoring intervention

State evolution still runs on all 63 nodes.

Two scoring regions are computed from the same episodes and final states:

1. `full`: all nodes `0..62` (diagnostic replication of SCALE-TOPOLOGY-11 scoring);
2. `interior`: fixed central nodes `16..46` inclusive (31 nodes).

The interior window is frozen before execution. It removes exactly 16 scoring nodes from each boundary and is not changed by task block, interaction scale, seed, or outcome.

The intervention is scoring-only. Boundary nodes still participate fully in state evolution and can influence interior nodes.

## Measurements

For both full and interior regions:

- target decodability = node-level global-majority target accuracy across original and nuisance twin;
- nuisance compression = `1 - final paired L1 distance / initial paired L1 distance`, clipped to [0,1], using only the scoring region for the distance;
- information efficiency = harmonic mean(target decodability, nuisance compression);
- capability = mean global-majority target accuracy across the same independent unrotated and rotated capability streams used in SCALE-TOPOLOGY-11.

The primary confirmatory metrics are the interior information-efficiency and interior capability values.

Full-line metrics are diagnostic but enter the boundary-specificity gate below.

## Peak rule

Reuse SCALE-PEAK-10 unchanged:

1. exact observed argmax over scales 4..15 within replicate and task geometry;
2. exact ties use arithmetic mean of tied scales;
3. geometry-level peak = median of five replicate peak locations;
4. no smoothing, interpolation, polynomial fitting, or post-outcome scale selection.

## Preregistered gates

The interior trial projection must pass the complete unchanged SCALE-PEAK-10 evaluator:

1. median peaks strictly interior to the scale grid;
2. information-efficiency peaks strictly ordered `peak(5) < peak(9) < peak(13)`;
3. capability peaks strictly ordered `peak(5) < peak(9) < peak(13)`;
4. block-13 minus block-5 median shift >= 2 for both metrics;
5. information-efficiency and capability peaks differ by <= 2 within each geometry;
6. information-efficiency moves outward block 5 -> 13 in >=4/5 paired replicates;
7. capability moves outward block 5 -> 13 in >=4/5 paired replicates.

Boundary specificity is additionally required: the full-line projection from the same fresh episodes must fail at least one capability-related SCALE-PEAK-10 gate among:

- `capability_strict_order`;
- `minimum_small_large_shift`;
- `within_geometry_alignment`;
- `paired_capability_outward`.

Thus a simple fresh-seed recovery on both scoring regions does not count as evidence for a boundary-scoring explanation.

Malformed coverage, seed mismatch, or invariant drift yields `INSUFFICIENT_EVIDENCE`.

`NOT_FALSIFIED_BY_DATA` requires both:
- all interior peak gates pass; and
- boundary specificity passes.

Otherwise the boundary-scoring explanation is `FALSIFIED_BY_DATA`.

## Interpretation boundary

A surviving result would support only:

> On this reflected-line toy substrate, excluding fixed endpoint-adjacent nodes from scoring restores the preregistered task-geometry-to-operating-scale relationship while full-line scoring on the same fresh episodes still fails a capability-related gate.

It would not prove that physical boundaries generally explain topology dependence, because boundary nodes remain causally active in evolution. A positive result would motivate a stronger boundary-condition intervention next.

No outcome-dependent retuning is permitted.
