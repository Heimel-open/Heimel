# SCALE-GEOMETRY-09 — Predictive task-geometry shift test

Status before execution: PREREGISTERED.

## Question

Does changing only the spatial correlation length of the task move the continuous information-efficiency and capability optima in the predicted direction?

The mechanistic prediction is directional: when task evidence forms larger contiguous spatial blocks, nearby messages become more redundant, so the useful interaction scale should move outward. Smaller blocks should favor a smaller interaction scale; larger blocks should favor a larger interaction scale.

This is a bounded toy-substrate mechanism test. It does not establish a universal law of intelligence or cognition.

## Prior evidence boundary

SCALE-EFFICIENCY-08 found nearby interior optima for information efficiency and independent capability on the fixed block-9 task. That result motivates this intervention but is not counted as confirmation here.

No SCALE-GEOMETRY-09 outcome may be used to alter the geometry set, score definitions, continuous model, thresholds, or gates below.

## Frozen substrate

Keep the execution substrate unchanged:

- 63 nodes on the same distance-labelled ring;
- interaction scales `1, 2, 4, 8, 16`;
- 3 synchronous rounds;
- fanout 4;
- one scalar state channel;
- same mean-message update rule;
- noise probability `0.10`;
- 256 episodes per probe stream;
- same node set, topology, initial-state encoding, compute budget and update-rule digests.

Fresh replicate seeds: `27027, 28028, 29029, 30030, 31031`.

## Intended intervention: task geometry only

Test three preregistered segmented block sizes:

- small geometry: `block = 5`;
- canonical geometry: `block = 9`;
- large geometry: `block = 13`.

Within a geometry, only `interaction_scale` varies. Across geometries, only the segmented block size varies. The ring, node count, update rule, rounds, fanout, state channel, noise rate and score rules remain fixed.

## Frozen information-efficiency probe

For every geometry × scale × replicate, generate 256 segmented majority episodes using the geometry's block size.

For each episode create a nuisance twin by randomly permuting the complete node-value multiset. The permutation preserves the global sum, majority target and evidence counts while changing spatial arrangement.

Measure:

- `target_decodability`: mean node-level majority-target accuracy across original and nuisance twin;
- `nuisance_compression`: `1 - final paired L1 distance / initial paired L1 distance`, clipped to `[0,1]`;
- `information_efficiency`: harmonic mean of target decodability and nuisance compression.

## Frozen independent capability probe

Capability is measured on separate random streams that are never reused by the efficiency probe.

For each geometry × scale × replicate:

1. generate 256 fresh segmented episodes with the geometry's block size and no rotation;
2. generate 256 fresh segmented episodes with a random rotation in `[0, block-1]`;
3. evolve each episode on the same frozen substrate;
4. score node-level majority-target accuracy;
5. `capability` is the mean accuracy across both independent streams.

The capability streams use deterministic seed domains distinct from the efficiency stream. Efficiency terms are not included in capability.

## Continuous response model

For each geometry independently, aggregate the five replicate means at each interaction scale.

Let `x = log2(interaction_scale)` and fit preregistered OLS quadratics:

`E_g(x) = a_E,g x^2 + b_E,g x + c_E,g`

`C_g(x) = a_C,g x^2 + b_C,g x + c_C,g`

When `a < 0`, the continuous optimum is `x* = -b/(2a)`.

The same fit is also computed within each replicate across the five scales for the paired directional-shift gate.

No polynomial degree or fitting rule may change after execution.

## Preregistered gates

SCALE-GEOMETRY-09 is `NOT_FALSIFIED_BY_DATA` only if all gates hold:

1. for every geometry, both aggregate efficiency and capability quadratics are concave (`a < 0`);
2. for every geometry, both aggregate vertices lie strictly inside the tested interval (`0 < x* < 4`);
3. within every geometry, aggregate efficiency and capability vertices differ by at most `0.75` log2-scale units;
4. aggregate efficiency vertices strictly increase with block size: `x*_E,5 < x*_E,9 < x*_E,13`;
5. aggregate capability vertices strictly increase with block size: `x*_C,5 < x*_C,9 < x*_C,13`;
6. the aggregate small-to-large shift is at least `0.25` log2 units for efficiency and at least `0.25` for capability;
7. in at least `4/5` paired fresh replicates, the fitted large-geometry efficiency vertex exceeds the fitted small-geometry efficiency vertex;
8. in at least `4/5` paired fresh replicates, the fitted large-geometry capability vertex exceeds the fitted small-geometry capability vertex;
9. each geometry × scale has exactly five valid replicates, and all non-geometry invariants are identical.

If a replicate-level quadratic is non-concave or has an out-of-range vertex, that replicate does not count as a positive directional shift; it does not invalidate the run by itself.

Malformed data, missing coverage or non-geometry invariant drift yields `INSUFFICIENT_EVIDENCE`. Any empirical gate failure yields `FALSIFIED_BY_DATA`.

## Interpretation boundary

A surviving result would support only this bounded claim:

> On this fixed toy ring substrate, changing task spatial correlation length causally moves the interaction-scale region that maximizes both information efficiency and independently measured task capability in the predicted direction.

That would be evidence for a geometry-dependent mechanism behind the scale optimum, not merely another replication of the same curve.

A failure is retained as evidence without retuning.
