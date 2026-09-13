# SCALE-BLOCKCROSS-27 — result

Status: `INVARIANT_BLOCK_RELATIONS_DETECTED`.

Canonical base: `6b163b43c01b1c736b49241bd1aae6fd18430db0`  
Preregistration: `11c0774dd06dc973e743f6549622c387a1fb53eb`

## Numerical correction

SCALE-BLOCKCROSS-26 was rejected because hard binary scoring at exactly zero was not numerically basis invariant.

This protocol used the preregistered symmetric stable score:

- margin > +1e-12 -> 1
- margin < -1e-12 -> 0
- |margin| <= 1e-12 -> 0.5

No #26 outcome was accepted into this inference.

Fresh seeds:

`167167..186186`, 20 replicates.

## Basis-invariance certificate

100 deterministic independent Haar rotations were applied inside every degenerate block.

- maximum elementwise projector change: `7.77e-16`
- maximum projector operator-norm change: `1.95e-15`
- certified worst-case pair-state margin perturbation: `4.79e-14`
- minimum distance of any canonical pair-state margin to the score thresholds +/-1e-12: `9.61e-13`

Because the perturbation bound is smaller than the nearest threshold distance, no stable capability category can change under the tested internal basis rotations.

The block-pair D statistics are therefore basis invariant under the frozen audit.

## Exact familywise inference

The scale-13 operator defines 12 maximal invariant singular-value blocks, yielding 66 fixed block pairs.

For each pair the same input-space projectors were evaluated under both scale 7 and scale 13.

Pair interaction:

`X_s=(C_++ + C_-- - C_+- - C_-+)/4`.

Scale-selective relational change:

`D=X_13-X_7`.

Familywise inference enumerated all:

`2^20 = 1,048,576`

paired sign-flip patterns and used the maximum T across all 66 relations.

No Monte Carlo approximation and no absolute effect-size threshold were used.

Result:

`48 / 66` block relations have positive mean D and one-sided familywise-adjusted `p <= 0.05`.

Primary status:

`INVARIANT_BLOCK_RELATIONS_DETECTED`.

## Strongest relations

| rank | blocks | X7 | X13 | D | T | FWER p |
|---:|---|---:|---:|---:|---:|---:|
| 1 | (0,1) | 0.0000433 | 0.0034644 | 0.0034211 | 25.09 | 9.54e-7 |
| 2 | (4,7) | -0.0024351 | -0.0001370 | 0.0022981 | 24.28 | 9.54e-7 |
| 3 | (6,8) | -0.0027982 | -0.0007017 | 0.0020965 | 20.32 | 9.54e-7 |
| 4 | (3,7) | -0.0016554 | 0.0001260 | 0.0017814 | 17.98 | 9.54e-7 |
| 5 | (5,8) | -0.0013467 | ~0 | 0.0013467 | 17.96 | 9.54e-7 |
| 6 | (6,7) | -0.0014507 | 0.0002024 | 0.0016531 | 16.52 | 9.54e-7 |
| 7 | (0,6) | -0.0009128 | 0.0006513 | 0.0015641 | 14.18 | 9.54e-7 |
| 8 | (3,4) | -0.0010341 | 0.0019783 | 0.0030124 | 13.83 | 9.54e-7 |
| 9 | (7,9) | -0.0016641 | 0 | 0.0016641 | 12.71 | 9.54e-7 |
| 10 | (8,11) | -0.0010301 | 0.0001268 | 0.0011569 | 12.58 | 9.54e-7 |

The exact minimum attainable adjusted p with 20 sign-flip replicates is `1/2^20 = 9.5367e-7`.

## Sign reversals

Across all 66 invariant relations:

- 25 change sign between scale 7 and scale 13;
- 21 of those sign-reversing relations are also positive-D and familywise significant.

Examples:

- blocks (3,7): `-0.001655 -> +0.000126`
- blocks (6,7): `-0.001451 -> +0.000202`
- blocks (0,6): `-0.000913 -> +0.000651`
- blocks (3,4): `-0.001034 -> +0.001978`

This is not a basis-vector statement. Each block is an invariant projector.

## Distributed rather than sparse

Positive-D mass concentration:

- strongest single relation: `6.53%`
- top 3: `16.68%`
- top 5: `24.24%`

Thus the observed scale-selective change is not dominated by one or a few block relations.

Combined with 48/66 significant positive relations, the result is better described as a broad reorganization of the relational interaction field.

## Native context

Stable native scale13-scale7 capability advantage:

`+0.033282`.

Bootstrap 95% CI:

`[0.030982, 0.035654]`.

## Interpretation

SCALE-BLOCKCROSS-27 is the first test in this chain where:

1. the objects are basis invariant;
2. the relations are explicit;
3. numerical decision-boundary ambiguity is handled symmetrically;
4. multiplicity is controlled exactly across the complete relation set.

The result supports:

> operating scale changes the functional contribution of a broad network of relations between invariant spectral blocks.

This is substantially different from a sparse-carrier explanation.

The scale-13 capability advantage is associated with a distributed relational reorganization: many relations that are destructive at scale 7 become less destructive or constructive at scale 13.

It does not yet establish whether that relational reorganization is necessary for the capability advantage as a whole.

The next hard test should intervene on the relational network itself while preserving each block's marginal contribution, asking whether destroying the cross-block organization collapses the scale-13 advantage.
