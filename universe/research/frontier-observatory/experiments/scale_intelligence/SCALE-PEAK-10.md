# SCALE-PEAK-10 — Dense nonparametric peak localization

Status before execution: PREREGISTERED.

## Question

When only task spatial correlation length changes, do the observed information-efficiency and independent capability peaks move outward in the predicted direction on a dense interaction-scale grid, without relying on a quadratic surrogate?

This follows SCALE-GEOMETRY-09. That protocol suggested aggregate outward movement for block sizes 5 → 9 → 13, but its preregistered quadratic localization failed for the largest geometry. SCALE-PEAK-10 does not reinterpret or retune SCALE-GEOMETRY-09. It replaces the continuous surrogate with a new, frozen nonparametric localization rule.

## Frozen substrate

Reuse the same 63-node distance-labelled ring and update rule:

- 63 nodes;
- 3 synchronous rounds;
- fanout 4 with offsets `[-2s, -s, +s, +2s]`;
- one scalar state channel;
- noise probability `0.10`;
- 256 episodes per probe stream;
- same node set, topology, initial-state encoding, compute budget and update rule digests.

Task geometry intervention: segmented block sizes `5, 9, 13` only.

Dense interaction-scale grid: every integer scale `4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15`.

The upper bound 15 keeps `2s <= 30`, below the 31-step maximum unique ring distance on 63 nodes, so the two nominal positive offsets do not cross the half-ring distance within the tested grid.

Fresh replicate seeds: `32032, 33033, 34034, 35035, 36036`.

## Frozen probes

### Information efficiency

Reuse the SCALE-COMPRESSION-07 / SCALE-GEOMETRY-09 nuisance probe definition:

1. Generate a geometry-matched segmented input.
2. Create a nuisance twin by permuting the complete node-value multiset, preserving global sum, majority target and evidence counts while altering spatial arrangement.
3. `target_decodability` = mean node-level majority-target accuracy across original and nuisance twin.
4. `nuisance_compression` = `1 - final paired L1 distance / initial paired L1 distance`, clipped to `[0,1]`.
5. `information_efficiency` = harmonic mean(target_decodability, nuisance_compression).

### Independent capability

Use separate deterministic RNG domains from the efficiency probe.

For each geometry/scale/replicate, capability is the mean node-level majority accuracy over:

- 256 unrotated geometry-matched segmented episodes; and
- 256 randomly rotated geometry-matched segmented episodes.

No information-efficiency term enters capability.

## Frozen nonparametric peak rule

For each geometry, replicate and metric independently:

1. inspect the 12 observed scores on scales 4–15;
2. find the maximum observed score;
3. collect all scales tied exactly at that maximum;
4. define that replicate's peak location as the arithmetic mean of the tied maximum scales.

For each geometry and metric, the aggregate peak location is the median of the five replicate peak locations.

No curve fitting, smoothing, interpolation, polynomial, post-hoc window, or outcome-dependent tie tolerance is allowed.

## Preregistered gates

SCALE-PEAK-10 is `NOT_FALSIFIED_BY_DATA` only if all gates hold:

1. complete coverage: exactly five paired replicates for every one of the 3 geometries × 12 scales, with identical non-geometry invariants;
2. all six median peak locations (3 geometries × 2 metrics) lie strictly inside the tested grid, i.e. `4 < median_peak < 15`;
3. information-efficiency median peaks are strictly ordered with geometry: `peak_E(5) < peak_E(9) < peak_E(13)`;
4. capability median peaks are strictly ordered with geometry: `peak_C(5) < peak_C(9) < peak_C(13)`;
5. small-to-large geometry shift is at least 2 scale units for both metrics: `peak(13) - peak(5) >= 2`;
6. within each geometry, information-efficiency and capability median peaks differ by at most 2 scale units;
7. paired replicate peaks move outward from block 5 to block 13 in at least 4/5 replicates for information efficiency;
8. paired replicate peaks move outward from block 5 to block 13 in at least 4/5 replicates for capability.

Malformed data, missing coverage or invariant drift yields `INSUFFICIENT_EVIDENCE`. Any other gate failure yields `FALSIFIED_BY_DATA`.

No gate or scale range may be changed after execution.

## Interpretation boundary

A surviving result would support only this bounded mechanism claim:

> On this fixed toy ring substrate, increasing the spatial correlation length of the task moves the empirically observed operating optimum toward larger interaction scales for both information efficiency and independent task capability.

It would not establish a universal scaling law, intelligence law, or a specific mathematical relationship between task geometry and optimal interaction scale.

Record the full result without retuning.