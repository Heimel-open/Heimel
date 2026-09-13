# SCALE-DECOUPLING-14 — Is information-efficiency necessary for capability peak location?

Status before canonical execution: PREREGISTERED.

## Primary objective

Falsify the claim that the previously observed information-efficiency optimum is causally necessary for the task-geometry-dependent capability optimum.

SCALE-BOUNDARY-DYNAMICS-13 produced the critical intervention: changing only endpoint address resolution left central capability peaks near 5/9/13 while information-efficiency peaks moved to roughly 5/5/6 under self-padding. This protocol tests that decoupling directly rather than treating curve alignment as mechanism.

## Canonical base

`cab3c0e89a24fb254ccf575720d0b1c85fd23cb9`

## Frozen design

Reuse SCALE-BOUNDARY-DYNAMICS-13 unchanged:

- 63-node line;
- central scoring nodes 16..46;
- task blocks 5, 9, 13;
- interaction scales every integer 4..15;
- 3 synchronous rounds;
- four message slots [-2s,-s,+s,+2s];
- scalar state and /5 update;
- reflected and self-padded endpoint address resolution;
- same task generator, nuisance twin, global-majority target and probe definitions;
- exact nonparametric peak rule from SCALE-PEAK-10.

Fresh paired seeds: `52052, 53053, 54054, 55055, 56056`.

The same generated episode is evaluated under both boundary conditions.

## Preregistered quantities

For each boundary condition, task block and replicate, locate:

- capability peak;
- information-efficiency peak.

Define per block:

- `C_shift = median(capability_peak_self_padded - capability_peak_reflected)`;
- `E_shift = median(efficiency_peak_self_padded - efficiency_peak_reflected)`;
- `decoupling = |E_shift - C_shift|`.

## Primary falsification target

The necessity claim is:

> A material intervention-induced movement of the information-efficiency optimum must be accompanied by a commensurate movement of the capability optimum.

It is falsified by data if all of the following hold:

1. complete paired coverage and invariant integrity;
2. reflected capability peaks retain strict task ordering 5 < 9 < 13;
3. self-padded capability peaks retain strict task ordering 5 < 9 < 13;
4. for at least one preregistered geometry among blocks 9 or 13, the absolute median efficiency-peak shift is >= 3 scale units;
5. for that same geometry, the absolute median capability-peak shift is <= 1 scale unit;
6. for that same geometry, at least 4/5 paired replicates show `|efficiency shift| >= 3` while `|capability shift| <= 1`.

Blocks 9 and 13 are the confirmatory geometries because SCALE-BOUNDARY-DYNAMICS-13 showed the large efficiency displacement there. Block 5 is retained as a negative-control diagnostic.

If the intervention does not again produce a material efficiency shift in either confirmatory geometry, verdict is `INSUFFICIENT_EVIDENCE`: the necessary perturbation was not reproduced.

If a material efficiency shift reproduces but capability shifts commensurately (>1 median scale unit, or fewer than 4/5 paired decoupled replicates), the necessity claim is `NOT_FALSIFIED_BY_DATA`.

No threshold or geometry selection may be changed after execution.

## Interpretation boundary

A falsified necessity claim would establish only that this measured information-efficiency optimum is not required to locate the capability optimum on this toy substrate. It would not establish what mechanism does generate the capability optimum.
