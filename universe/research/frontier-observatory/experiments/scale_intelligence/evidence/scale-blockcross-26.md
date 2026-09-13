# SCALE-BLOCKCROSS-26 — integrity failure

Status: `INSUFFICIENT_EVIDENCE`.

Canonical base: `b1dcd3ba818cae05897680d19c815bdc0943760b`  
Preregistration: `874ddd2305ffafbd1fbadb24dd187ed3baab76af`

## What failed

The preregistered integrity gate required the block-pair interaction statistic to remain invariant within `1e-12` under internal orthogonal basis rotations of degenerate singular blocks.

A deterministic Haar rotation changed each block projector only at floating-point roundoff:

`max |P_rotated - P_native| = 1.94e-16`.

The underlying mathematical projectors are therefore unchanged to numerical precision.

However, the binary capability score uses a hard decision at target-aligned margin zero. Tiny floating-point changes around exactly/near-zero pair-intervention margins changed several binary outcomes.

Already the first checked valid basis rotation produced:

`max |D_rotated - D_native| = 4.7253e-06`.

This exceeds the frozen `1e-12` D-invariance gate by several orders of magnitude.

The protocol therefore stops at the integrity layer.

## Consequence

No confirmatory inference from the 20 fresh SCALE-BLOCKCROSS-26 seeds is accepted.

In particular, apparent familywise-significant block relations observed before the audit failure must not be promoted as evidence.

The failure is numerical/estimand-level, not evidence that the relational hypothesis is false.

## Source of the problem

The block projectors are basis invariant.

The discontinuity comes from the binary scoring rule at exactly zero margin:

`score = 1[margin >= 0]`.

A representation change of order `1e-16` can therefore change the score by a full binary unit for an observation lying on the boundary.

## Required correction

The next protocol must make the decision-boundary treatment explicit and symmetric before fresh data.

A numerically stable rule is:

- margin > `1e-12`: success = 1
- margin < `-1e-12`: success = 0
- |margin| <= `1e-12`: tie = 0.5

The `1e-12` tolerance is inherited from the existing numerical-integrity tolerance; it is not an effect-size gate.

The corrected experiment must use new fresh seeds and repeat the full exact familywise test.
