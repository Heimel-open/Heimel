# SCALE-CROSSPROJECTOR-25 — result

Status: `NOT_CROSSPROJECTOR_OUTLIER_AGAINST_NULL`.

Canonical base: `25c79cd05b662d44ea6a919fdd47aede5d2e5fd7`  
Preregistration: `65f65c19c856fd87b33c1c03396271466b0c2350`

## Basis-invariant relational intervention

The fixed target projectors were:

- scale 7: exact degenerate right-singular block {6,7,8}, rank 3;
- scale 13: exact degenerate right-singular block {7,8,9,10,11}, rank 5.

For centered residual r:

`y_T = B P r`

`y_R = B(Q-P)r`.

Target and remainder contributions were independently sign-flipped in all four states.

The balanced nonlinear cross-term was:

`X = (C_++ + C_-- - C_+- - C_-+)/4`.

This cancels the individual target/remainder main effects and isolates their capability interaction.

## Fresh target result

Fresh seeds:

`117117..126126`.

Target cross-term:

- scale 7: `X_7 = 0.00006458`;
- scale 13: `X_13 = 0.00335496`.

Scale-selective difference:

`DeltaX_target = +0.00329039`.

Fresh replicate DeltaX values:

- 0.0029454
- 0.0047253
- 0.0037172
- 0.0036227
- 0.0046308
- 0.0024887
- 0.0026147
- 0.0014018
- 0.0036700
- 0.0030872

Bootstrap 95% CI:

`[0.002682, 0.003868]`.

The invariant target-vs-rest relation is therefore consistently more constructive at scale 13 than scale 7.

However, that effect is not unusually large.

## Random-projector null

1,000 paired Haar-random centered projectors:

- rank 3 at scale 7;
- rank 5 at scale 13;
- RNG seed `250025`.

Random DeltaX distribution:

- mean: `0.0187572`;
- std: `0.0044532`;
- min: `0.0053238`;
- max: `0.0340238`.

All `1000/1000` random draws exceeded the target DeltaX.

Primary empirical p:

`p = 1.0`.

Thus the fixed invariant target-vs-rest cross-term is not an outlier against the dimension-matched relational null.

## Operator-gain diagnostic

Target operator gains:

- scale 7: `||BP||_F^2 = 0.3306080`;
- scale 13: `||BP||_F^2 = 2.0213430`.

Random means:

- scale 7: `0.1802333`;
- scale 13: `0.4854128`.

Target gain percentiles:

- scale 7: `99.6%`;
- scale 13: `100.0%`.

Therefore the random null did not beat target because random projectors generally had more operator gain. The target projectors are unusually high-gain while still producing unusually small gross target-vs-rest cross-terms.

Random-null Spearman diagnostics:

- gain7 vs DeltaX: `-0.2276`;
- gain13 vs DeltaX: `+0.3853`;
- log(gain13/gain7) vs DeltaX: `+0.3900`.

The 100 gain-nearest random draws all still exceeded target DeltaX, but their maximum paired log-gain distance was `1.358`, so this nearest-gain diagnostic is descriptive rather than a tightly matched conditional null.

## Native context

Fresh native capability:

- scale 7: `0.7970073`;
- scale 13: `0.8298198`;
- advantage: `+0.0328125`.

Bootstrap 95% CI:

`[0.029801, 0.036196]`.

## Integrity

- max projector symmetry/idempotence error: `3.61e-16`;
- max target+complement decomposition error: `1.11e-16`;
- max projector change under internal basis rotations: `3.33e-16`.

## Interpretation

SCALE-CROSSPROJECTOR-25 falsifies another coarse relational explanation:

> the important scale-dependent mechanism is simply the nonlinear interaction between the implicated invariant subspace and the entire rest of the centered system.

That relation does become more constructive at scale 13, but it is weaker than every random dimension-matched projector relation tested.

Combined with SCALE-BASIS-23 and SCALE-PROJECTOR-24, the remaining direction is narrower:

> the signal is likely carried by structured interactions between multiple invariant spectral blocks, not by one SVD pair, one whole invariant subspace, or one target-vs-rest partition.

The next experiment should decompose the operator into maximal invariant singular-value blocks and compute exact basis-invariant pairwise cross-terms between those blocks. That is the first representation where the object itself is invariant and the relation remains explicit.
