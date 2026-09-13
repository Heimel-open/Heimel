# SCALE-COMPRESSION-07 result

Result: `FALSIFIED_BY_DATA`.

The protocol was frozen at preregistration commit `79a46e44da238825567226903adc14da06622e57` before the fresh-seed run.

## Aggregate results

| scale | target decodability | nuisance compression | sufficient compression |
|---:|---:|---:|---:|
| 1 | 0.70817 | 0.36466 | 0.48140 |
| 2 | 0.71856 | 0.48708 | 0.58057 |
| 4 | 0.75278 | 0.60463 | 0.67060 |
| 8 | 0.78717 | 0.67036 | 0.72402 |
| 16 | 0.75853 | 0.61520 | 0.67931 |

Scale 8 had the highest mean value on all three measured quantities and beat both scale 1 and scale 16 on the joint sufficient-compression score in all `5/5` paired fresh replicates.

Observed scale-8 gains:

- sufficient compression vs scale 1: `+0.24262`;
- sufficient compression vs scale 16: `+0.04471`;
- target decodability vs scale 1: `+0.07900`;
- target decodability vs scale 16: `+0.02863`;
- nuisance compression vs scale 1: `+0.30570`.

## Why the frozen verdict is negative

Five of six empirical gates passed. The preregistered scale-8 target-decodability advantage over scale 16 was required to be at least `0.03`; the observed advantage was `0.0286334`.

That gate therefore fails. It is not rounded upward and the threshold is not changed after observation.

## What the data do support diagnostically

The fresh probe reproduces a strong interior optimum: scale 8 simultaneously removes substantially more task-irrelevant spatial arrangement than scale 1 and retains more node-level target information than either tested extreme. The harmonic joint score also peaks at scale 8.

However, because the confirmatory high-scale decodability margin missed its frozen threshold, the preregistered task-sufficient-compression explanation is not accepted as confirmed.

A future protocol may test whether the relevant effect is a continuous information-efficiency optimum rather than a fixed minimum decodability margin. That would be a new hypothesis and must not retroactively alter this result.

## Boundary

This is a deterministic CPU-only toy ring with a global-majority task. It is not evidence for general intelligence, human understanding, consciousness, or a universal information-bottleneck law.

Validation: six logical evaluator cases passed locally. Execution used five scales, five fresh replicates per scale and 256 paired nuisance episodes per replicate.
