# SCALE-TOPOLOGY-11 — Substrate transfer of geometry-to-optimum shift

Status before canonical execution: PREREGISTERED.

## Question

Does the directional relationship from SCALE-PEAK-10 survive a topology transfer?

Specifically: when task spatial correlation length increases from block 5 to 9 to 13, do the empirically observed information-efficiency and independent capability peaks move outward on a non-periodic reflected-line substrate?

## Canonical base

`6062231d1ee95348cf3dd53aad576d80c925dbc3`

## Frozen substrate transfer

Keep the SCALE-PEAK-10 experimental structure, but replace the 63-node periodic ring with a 63-node reflected line.

Nodes remain indexed `0..62`. The four message offsets remain `[-2s, -s, +s, +2s]`, with one self value plus four message slots averaged by the same `/5` update. There are still 3 synchronous rounds, fanout 4, and one scalar state channel.

The only substrate change is address resolution at the ends:

- ring: `(i + offset) mod 63`;
- reflected line: mirror the address at endpoints 0 and 62 using period `2*(63-1)=124`;
- exact mapping: `r = j mod 124`; if `r >= 63`, use `124-r`.

This is a non-periodic topology. Boundary reflection may make two message slots resolve to the same node; message-slot count and arithmetic budget remain fixed.

The segmented task generator, nuisance permutation, noise rate, scoring definitions, and independent capability streams remain unchanged.

## Frozen conditions

- task blocks: `5, 9, 13`;
- interaction scales: every integer `4..15`;
- fresh replicate seeds: `37037, 38038, 39039, 40040, 41041`;
- 256 episodes per probe stream;
- node count 63;
- 3 rounds;
- fanout/message slots 4;
- one scalar state channel;
- same self/peer weights and `/5` normalizer;
- same `NOISE_P = 0.10`;
- same task generators apart from the preregistered task-block intervention.

## Frozen measurements

Information efficiency is unchanged from SCALE-COMPRESSION-07 / SCALE-PEAK-10:

- `target_decodability`: mean node-level majority-target accuracy across an episode and its nuisance-permuted twin;
- `nuisance_compression`: `1 - final paired L1 distance / initial paired L1 distance`, clipped to `[0,1]`;
- `information_efficiency`: harmonic mean of target decodability and nuisance compression.

Independent capability is unchanged from SCALE-GEOMETRY-09 / SCALE-PEAK-10:

- one unrotated geometry-matched majority stream;
- one independently seeded randomly rotated geometry-matched stream;
- capability = mean node-level majority accuracy across both streams.

The efficiency and capability episode streams use separate deterministic RNG domains.

## Frozen peak rule

Reuse the SCALE-PEAK-10 nonparametric rule unchanged:

1. within each replicate and geometry, peak = exact observed argmax over scales 4..15;
2. if multiple scales have exactly equal maximum score, peak location = arithmetic mean of the tied scales;
3. geometry-level peak = median of the five replicate peak locations;
4. no smoothing, interpolation, polynomial fit, threshold retuning, or post-outcome scale selection.

## Preregistered gates

Reuse the SCALE-PEAK-10 evaluator and thresholds unchanged. `NOT_FALSIFIED_BY_DATA` requires all of the following:

1. complete paired coverage and identical fixed-substrate invariants;
2. every median peak is strictly inside the scale grid (`4 < peak < 15`);
3. information-efficiency median peaks are strictly ordered: `peak(5) < peak(9) < peak(13)`;
4. capability median peaks are strictly ordered: `peak(5) < peak(9) < peak(13)`;
5. block-13 minus block-5 median peak shift is at least 2 scale units for both metrics;
6. information-efficiency and capability median peaks differ by at most 2 scale units within each task geometry;
7. information-efficiency peak moves outward from block 5 to block 13 in at least 4/5 paired replicates;
8. capability peak moves outward from block 5 to block 13 in at least 4/5 paired replicates.

Malformed/missing data or invariant drift yields `INSUFFICIENT_EVIDENCE`. Any empirical gate failure yields `FALSIFIED_BY_DATA`.

## Interpretation boundary

A surviving result would support only the bounded transfer claim:

> The task-geometry-to-operating-scale relationship observed on the periodic ring also survives on this non-periodic reflected-line toy substrate.

A failure would mean the mechanism is not topology-invariant under this transfer. It would not by itself distinguish whether the failure is caused by boundaries, altered path structure, reflected duplicate message targets, or another topology-specific feature.

No outcome-dependent retuning is permitted. Record the complete result.