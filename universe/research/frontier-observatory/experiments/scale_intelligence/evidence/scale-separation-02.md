# SCALE-SEPARATION-02 result

Outcome: `NOT_FALSIFIED_BY_DATA`.

Preregistered protocol commit: `2c9d9460dacd4c29f6a1f827b3fec69d7b8d8e6d`.

Fresh replication seeds: `404, 505, 606`.

All non-scale invariant digests remained identical. Five scales were tested: `1, 2, 4, 8, 16`, with three replicates per scale and 256 episodes per task family.

## Frozen gates

- each integration/transfer metric spread >= 0.08;
- at least two integration/transfer metrics share one best scale;
- counterfactual adaptation spread <= 0.03;
- counterfactual adaptation mean <= 0.10.

No threshold was changed after outcome.

## Result

Scale-wise means:

| scale | task success | transfer | distributed integration | counterfactual adaptation |
|---:|---:|---:|---:|---:|
| 1 | 0.65063 | 0.63817 | 0.45582 | 0.03590 |
| 2 | 0.66865 | 0.67752 | 0.59569 | 0.04036 |
| 4 | 0.74120 | 0.73136 | 0.73545 | 0.04078 |
| 8 | 0.81240 | 0.79216 | 0.83399 | 0.04045 |
| 16 | 0.75632 | 0.72731 | 0.75594 | 0.04055 |

Observed integration/transfer spreads:

- task success: `0.16177`;
- cross-context transfer: `0.15400`;
- distributed integration: `0.37817`.

All three peak at interaction scale `8`.

Counterfactual adaptation:

- mean across scales: `0.03961`;
- scale spread: `0.00488`.

## Interpretation

The narrower separation observed in SCALE-INTELLIGENCE-01 replicated on fresh seeds.

On this fixed toy substrate, interaction scale materially changes task success, transfer and distributed integration, with a common optimum at scale 8. The same scale intervention does not materially change the counterfactual adaptation metric, which remains low across the entire sweep.

This does not rescue the falsified broad intelligence-like phenotype from SCALE-INTELLIGENCE-01. It supports only the bounded claim that scale is a causal control variable for the tested integration/transfer functions while scale alone is insufficient to produce the tested counterfactual adaptation behavior.

The next causal intervention should keep the scale sweep fixed and add exactly one candidate adaptation-enabling mechanism.
