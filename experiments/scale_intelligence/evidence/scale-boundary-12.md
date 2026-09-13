# SCALE-BOUNDARY-12 — result

Status: `NOT_FALSIFIED_BY_DATA`.

Canonical base: `6fce414ddff6e503d8c7ccdccd560eba75b63b48`  
Preregistration: `d887082aa4f1883391b5d99eb74b0b955d7bfff7`

## Frozen design

- unchanged 63-node reflected-line substrate from SCALE-TOPOLOGY-11;
- task blocks `5, 9, 13`;
- scales every integer `4..15`;
- fresh paired seeds `42042, 43043, 44044, 45045, 46046`;
- 256 episodes per probe stream;
- same state evolution for both scoring conditions;
- full scoring: nodes `0..62`;
- interior scoring: fixed nodes `16..46` (31 nodes);
- boundary nodes remain causally active in evolution;
- same exact nonparametric peak rule as SCALE-PEAK-10.

## Confirmatory result

Interior scoring passed the complete frozen SCALE-PEAK-10 relation.

Median peak locations:

| task block | interior efficiency | interior capability |
|---:|---:|---:|
| 5 | 5 | 5 |
| 9 | 9 | 9 |
| 13 | 13 | 13 |

Paired outward movement block 5 -> 13:

- interior efficiency: `5/5`;
- interior capability: `5/5`.

All interior gates passed.

Interior replicate peaks:

- capability block 5: `[6, 5, 5, 7, 5]`;
- capability block 9: `[9, 9, 9, 9, 9]`;
- capability block 13: `[13, 13, 13, 13, 13]`;
- efficiency block 5: `[5, 5, 5, 5, 5]`;
- efficiency block 9: `[9, 10, 9, 9, 9]`;
- efficiency block 13: `[13, 13, 13, 15, 13]`.

## Boundary-specificity control

The full-line projection from the exact same fresh episodes remained `FALSIFIED_BY_DATA`.

Full-line median peaks:

| task block | full efficiency | full capability |
|---:|---:|---:|
| 5 | 9 | 11 |
| 9 | 11 | 9 |
| 13 | 13 | 13 |

Capability-related full-line gates that failed:

- `capability_strict_order`;
- `paired_capability_outward`.

Full-line capability moved outward block 5 -> 13 in only `3/5` paired replicates.

Thus the preregistered boundary-specificity gate passed: the same substrate, tasks, seeds and evolved states fail under full-line scoring but satisfy the complete relation under the frozen central scoring window.

## Validation

- evaluator synthetic tests: `5/5` passed locally;
- canonical run: 180 cells, CPU-only;
- no model/API calls;
- trial digest: `sha256:b8c1580c17ff3bc893319e6d943c12bdfb8e87b5801bc819a89813bd4dbad3df`;
- compact result digest: `sha256:174ac5da59a3d1ac5a071ebbcdb157c07ed71ff73f2cfe226a1def058e5f9fa9`.

## Evidence boundary

This supports a measurement-boundary explanation on this reflected-line toy substrate: endpoint-adjacent nodes are sufficient to disrupt the full-line peak relation, while a preregistered central scoring region recovers the geometry-to-operating-scale ordering.

It does not yet show that boundary nodes are the causal source inside the dynamics, because they still participate in evolution and can influence the interior. The next hard test should intervene on the boundary condition itself while keeping the scoring region fixed.
