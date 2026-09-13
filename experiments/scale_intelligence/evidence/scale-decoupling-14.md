# SCALE-DECOUPLING-14 — result

Status: `FALSIFIED_BY_DATA`.

Canonical base: `cab3c0e89a24fb254ccf575720d0b1c85fd23cb9`  
Preregistration: `821458c277d5be260e013f91da6c21a90929fe8f`

## Canonical run

Fresh paired seeds: `52052, 53053, 54054, 55055, 56056`.

360 condition-cells, 256 episodes per probe stream, CPU-only, no model/API calls.

Median peaks:

| block | reflected efficiency | self-padded efficiency | reflected capability | self-padded capability |
|---:|---:|---:|---:|---:|
| 5 | 5 | 5 | 5 | 5 |
| 9 | 9 | 6 | 9 | 9 |
| 13 | 13 | 6 | 13 | 13 |

Confirmatory paired shifts:

- block 9 efficiency deltas: `[-3, 0, -4, -4, -3]`, median `-3`;
- block 9 capability deltas: `[0, 0, 0, 0, 0]`, median `0`;
- block 9 paired decoupled criterion: `4/5`;
- block 13 efficiency deltas: `[-7, -7, -7, -6, -6]`, median `-7`;
- block 13 capability deltas: `[-1, 0, 0, 0, 0]`, median `0`;
- block 13 paired decoupled criterion: `5/5`.

Capability task ordering remained strict under both boundary conditions: `5 < 9 < 13`.

Both preregistered confirmatory geometries therefore satisfy the falsification criterion: a material information-efficiency peak displacement occurred without a commensurate capability peak displacement.

## Conclusion

The necessity claim is falsified on this toy substrate:

> The measured information-efficiency optimum is not causally necessary for locating the task-geometry-dependent capability optimum.

This does not identify the mechanism that generates the capability optimum. It removes information-efficiency peak alignment as a sufficient mechanistic explanation and makes the next target the invariant carried by capability across the boundary intervention.
