# SCALE-PROJECTOR-24 — result

Status: `NOT_PROJECTOR_EFFECT_OUTLIER_AGAINST_NULL`.

Canonical base: `4d39c18f9b446f469d15458de02d0dcdd80fd623`  
Preregistration: `82d816a5d53677445443a1f0b71b6edee1d88e41`

## Basis-invariant target

The prior SVD labels were replaced by invariant projectors:

- scale 7: right-singular projector onto the degenerate block {6,7,8}, dimension 3;
- scale 13: right-singular projector onto the degenerate block {7,8,9,10,11}, dimension 5.

For centered input residual r:

`y_target = B_s P_s r`.

The causal intervention flipped only that full projector contribution:

`y_flip = y_native - 2 y_target`.

No individual SVD vector entered the target definition.

## Target causal effect

Fresh pooled capability:

- scale 7 native: `0.7959740`;
- scale 7 target-projector flip: `0.7970136`;
- `E_7 = native - flip = -0.0010396`.

- scale 13 native: `0.8286353`;
- scale 13 target-projector flip: `0.8202495`;
- `E_13 = +0.0083858`.

Scale-selective target effect:

`DeltaE_target = E_13 - E_7 = +0.0094254`.

Across 10 fresh replicates, bootstrap 95% CI:

`[0.008304, 0.010654]`.

Native scale13-scale7 capability advantage on the same data:

`+0.0326613`, bootstrap 95% CI `[0.029971, 0.035276]`.

## Dimension-matched random-subspace null

1,000 paired Haar-random centered input subspaces were tested:

- dimension 3 at scale 7;
- dimension 5 at scale 13;
- deterministic PCG64 seed `240024`.

For each random subspace, the identical projector-contribution flip was applied.

Random scale-selective effects:

- mean: `0.0461339`;
- standard deviation: `0.0088720`;
- minimum: `0.0214718`;
- maximum: `0.0725680`.

All `1000/1000` random draws produced a larger DeltaE than the target projector.

Primary one-sided empirical p:

`p = 1.0`.

Lower-tail diagnostic:

`p = 0.000999`.

Thus the fixed invariant target projector is not an unusually strong gross causal carrier under the preregistered dimension-matched random-subspace null. It is unusually weak relative to that null.

## Task-overlap diagnostic

Basis-invariant captured residual energy:

Scale 7 target:
- overlap: `0.0791205`;
- random dimension-3 mean: `0.0482372`;
- target percentile: `99.7%`;
- upper-tail p: `0.003996`.

Scale 13 target:
- overlap: `0.0341820`;
- random dimension-5 mean: `0.0805784`;
- target percentile: `0.0%`;
- lower-tail p: `0.000999`.

This directly rejects the simple explanation that the scale-13 target subspace becomes useful because it captures more of the task residual. It captures markedly less residual energy than random dimension-matched subspaces.

## Integrity

- maximum target-projector symmetry/idempotence error: `3.61e-16`;
- maximum operator SVD reconstruction error: `1.18e-15`;
- maximum projector change under 1,000 internal Haar basis rotations: `3.33e-16`.

The projector intervention is therefore basis invariant to numerical precision.

## Interpretation

SCALE-PROJECTOR-24 falsifies the next simple mechanism:

> the degenerate invariant subspace implicated by prior pair results is itself an unusually strong gross causal carrier at scale 13.

It is not.

The prior pair/phase signal therefore appears to depend on internal relational structure within or between invariant components rather than merely the amount of task state routed through the whole degenerate subspace.

A caution remains: the random null matched dimension, not operator gain. Random subspaces can contain higher-gain singular directions than the fixed mid-spectrum target. Therefore this result does not eliminate the invariant subspace from the mechanism. It eliminates the unqualified "whole-subspace causal strength" explanation.

The next clean test should match both subspace dimension and operator gain, or formulate the mechanism directly as a basis-invariant cross-term between invariant spectral projectors.
