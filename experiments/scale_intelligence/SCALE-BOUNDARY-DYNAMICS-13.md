# SCALE-BOUNDARY-DYNAMICS-13 — Causal boundary-condition intervention

Status before canonical execution: PREREGISTERED.

## Question

Does the boundary condition itself causally move the central operating-scale optimum on the reflected-line toy substrate?

SCALE-TOPOLOGY-11 failed mainly at block-5 capability under full-line scoring. SCALE-BOUNDARY-12 showed that a fixed central scoring window recovers the geometry-to-operating-scale relation while boundary-adjacent scoring still fails. This protocol now changes the boundary dynamics while keeping central scoring fixed.

## Canonical base

`99a75b22f3de4239fef380ca2e82bc441f504654`

## Frozen substrate and task

Keep unchanged:

- 63 nodes indexed `0..62`;
- task blocks `5, 9, 13`;
- interaction scales every integer `4..15`;
- 3 synchronous rounds;
- four message slots `[-2s,-s,+s,+2s]`;
- one scalar state channel;
- self plus four messages averaged by `/5`;
- same segmented generator, nuisance permutation, noise rate and global-majority target;
- scoring only on fixed central nodes `16..46` inclusive;
- same exact nonparametric peak rule as SCALE-PEAK-10.

Fresh paired seeds: `47047, 48048, 49049, 50050, 51051`.

The exact same generated episode is evolved under both boundary conditions before scoring.

## Boundary intervention

Two conditions:

1. `reflected`: unchanged SCALE-TOPOLOGY-11 mapping. Out-of-range addresses mirror at endpoints.
2. `self_padded`: if a message address is outside `0..62`, that message slot resolves to the receiving node itself.

Both conditions therefore keep:

- four message slots;
- identical arithmetic count;
- identical `/5` normalization;
- identical rounds and state dimensionality.

Only address resolution at the boundary changes.

## Frozen measurements

For the central scoring window `16..46`:

- target decodability;
- nuisance compression;
- information efficiency = harmonic mean(target decodability, nuisance compression);
- capability = mean global-majority accuracy across the same independent unrotated and rotated streams used previously.

Each boundary condition is separately projected through the unchanged SCALE-PEAK-10 evaluator.

## Primary causal endpoint

The failure locus from SCALE-TOPOLOGY-11 is preregistered as the sole primary endpoint:

`block-5 central capability peak location`.

For each fresh replicate:

`delta_r = peak_self_padded_r - peak_reflected_r`.

A material boundary-induced peak shift requires all:

1. both boundary conditions have valid complete paired coverage;
2. the reflected central projection is `NOT_FALSIFIED_BY_DATA` under the unchanged SCALE-PEAK-10 relation;
3. the self-padded central projection is `NOT_FALSIFIED_BY_DATA` under the unchanged SCALE-PEAK-10 relation;
4. absolute median block-5 capability peak shift is at least `2.0` scale units;
5. at least `4/5` non-zero paired deltas have the same sign as the median shift.

No direction is predicted in advance; only coherent non-zero movement is tested.

If gates 1-3 hold but gates 4-5 fail, the claim that boundary condition materially moves the central block-5 operating-scale peak is `FALSIFIED_BY_DATA`.

Malformed data, invariant drift, or failure of either condition's geometry relation yields `INSUFFICIENT_EVIDENCE` for the causal comparison rather than a positive result.

## Secondary diagnostics

Record, without using them to rescue the primary claim:

- peak deltas for information efficiency at block 5;
- peak deltas for both metrics at blocks 9 and 13;
- aggregate score differences by scale;
- per-replicate peak locations.

## Interpretation boundary

A surviving result would support only:

> On this fixed toy line substrate, changing endpoint address resolution while holding central scoring and compute fixed causally shifts the block-5 capability operating-scale peak.

A falsified result would mean that the measurement-boundary effect found in SCALE-BOUNDARY-12 does not imply a material boundary-condition-induced movement of the central block-5 peak under this intervention.

No outcome-dependent retuning is permitted.
