# SCALE-EFFICIENCY-08 — result

Outcome: `NOT_FALSIFIED_BY_DATA`.

The preregistered continuous response test survived all seven gates on five fresh replicates per scale.

## Aggregate result

| scale | information efficiency | capability |
| ---: | ---: | ---: |
| 1 | 0.4791524 | 0.6477431 |
| 2 | 0.5803205 | 0.6771143 |
| 4 | 0.6664467 | 0.7407056 |
| 8 | 0.7220778 | 0.8097656 |
| 16 | 0.6794156 | 0.7442150 |

Both observed curves rise from scale 1 through scale 8 and then fall at scale 16.

## Continuous fit

Using the preregistered OLS quadratic in `x = log2(scale)`:

- information-efficiency curvature: `a = -0.0227254235`;
- capability curvature: `a = -0.0131696429`;
- information-efficiency vertex: `x = 3.1931214632`, corresponding to scale `9.1458766596`;
- capability vertex: `x = 3.2361581921`, corresponding to scale `9.4228154756`;
- vertex distance: `0.0430367289` log2-scale units;
- aggregate Spearman rank correlation: `0.9999999999999998`;
- interior information-efficiency winner: `5/5` fresh replicates.

All preregistered gates passed without threshold or model changes.

## What this supports

On this fixed toy substrate and tested range, information efficiency and independently measured task capability are both consistent with very nearby interior optima rather than monotonic improvement as interaction scale increases.

The best-fitting continuous region is near scale 9, while scale 8 is the best of the five actually tested scales.

## What this does not support

This does not prove a universal information bottleneck law, identify a universal intelligence scale, establish human understanding, or show that a quadratic is the true mechanism. Five discrete scales are being summarized by a preregistered continuous surrogate.

A stronger next test would perturb topology/task geometry while preserving the measurement contract and ask whether the optimum moves predictably with the relation between interaction scale and task structure, rather than remaining numerically near 8–9.

Validation: 7/7 evaluator cases passed locally; CPU-only execution.