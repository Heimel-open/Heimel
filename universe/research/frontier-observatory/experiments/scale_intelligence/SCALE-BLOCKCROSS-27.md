# SCALE-BLOCKCROSS-27 — Numerically stable invariant block relations

Status before confirmatory execution: PREREGISTERED.

## Canonical base

`6b163b43c01b1c736b49241bd1aae6fd18430db0`

## Motivation

SCALE-BLOCKCROSS-26 failed its numerical basis-invariance gate because a hard binary decision at exactly zero margin allowed floating-point perturbations of mathematically identical projectors to alter a small number of outcomes.

No confirmatory inference from #26 was accepted.

This protocol changes only the treatment of numerically unresolved decision-boundary ties.

## Frozen invariant blocks

Use the same scale-13 operator-defined maximal singular-value blocks as #26:

0. {0,1,2,3}, dim 4
1. {4}, dim 1
2. {5}, dim 1
3. {6}, dim 1
4. {7,8,9,10,11}, dim 5
5. {12,13,14,15,16}, dim 5
6. {17}, dim 1
7. {18,19,20,21,22}, dim 5
8. {23}, dim 1
9. {24,25,26,27}, dim 4
10. {28,29}, dim 2
11. {30}, dim 1

All objects are orthogonal projectors. There are 66 fixed block pairs.

## Stable capability score

Let m be target-aligned decision margin.

Use the existing numerical-integrity tolerance `epsilon = 1e-12`:

- if m > +epsilon: score = 1
- if m < -epsilon: score = 0
- if |m| <= epsilon: score = 0.5

The 0.5 tie value is symmetric between the two target signs and prevents arbitrary floating-point orientation from turning an unresolved exact boundary into a full success or failure.

This epsilon is a numerical tolerance inherited from the invariant tests, not an effect-size threshold.

## Excluded seeds

All seeds used in #26 and its numerical validation are excluded:
`147147..166166`.

Earlier pilot seeds `127127..146146` remain excluded as well.

## Fresh confirmatory seeds

`167167,168168,169169,170170,171171,172172,173173,174174,175175,176176,177177,178178,179179,180180,181181,182182,183183,184184,185185,186186`.

Exactly 20 fresh replicates.

## Pair interaction

For each fixed block pair (P_a,P_b), apply the same projectors under both B_7 and B_13.

All other contributions remain native.

Evaluate stable capability in four sign states and define:

`X_s(a,b) = (C_++ + C_-- - C_+- - C_-+)/4`.

Scale-selective relational change:

`D(a,b)=X_13(a,b)-X_7(a,b)`.

## Primary exact familywise test

For each of the 66 pairs, compute replicate-level D.

Observed statistic:

`T=mean(D)/(sd(D)/sqrt(20))`.

Enumerate all `2^20=1,048,576` paired sign-flip patterns. Each replicate sign multiplies its complete 66-dimensional D vector, preserving dependence across relations.

For each pattern compute the maximum T across all 66 pairs.

Adjusted one-sided familywise p:

`p_FWER(j)=count(T_max >= T_observed(j))/2^20`.

No Monte Carlo approximation and no absolute effect-size threshold.

Classification:

- `INVARIANT_BLOCK_RELATIONS_DETECTED` if at least one pair has mean D > 0 and p_FWER <=0.05;
- `NO_INVARIANT_BLOCK_RELATION_DETECTED` otherwise.

## Basis-invariance gate

Before accepting inference, perform 100 deterministic independent Haar rotations inside every degenerate block, NumPy PCG64 seed `270027`.

For each rotation:
- projector matrices must agree within 1e-12;
- recomputed stable block-pair D values must agree with canonical D within 1e-12.

Any failure => `INSUFFICIENT_EVIDENCE`.

## Diagnostics

Report:
- number of FWER-significant positive relations;
- strongest 10;
- number of significant sign reversals;
- total number of sign reversals;
- positive-D concentration top1/top3/top5;
- native scale13-scale7 stable capability advantage;
- block dimensions, singular values, residual overlap and operator gains.

None alter primary classification.

## Interpretation boundary

A positive result supports only that one or more basis-invariant spectral-block relations change their functional contribution with operating scale.

A broad set of significant relations would support distributed relational reorganization rather than a single sparse mechanism.

No post-outcome pair selection or threshold changes are permitted.
