# SCALE-BLOCKCROSS-26 — Basis-invariant spectral-block relations

Status before confirmatory execution: PREREGISTERED.

## Why this experiment

SCALE-BASIS-23 showed that individual SVD vectors inside degenerate singular subspaces are not unique physical objects.

SCALE-PROJECTOR-24 and SCALE-CROSSPROJECTOR-25 then rejected two coarse invariant explanations:
- the whole implicated subspace as a gross causal carrier;
- the implicated subspace versus the whole remainder as one aggregate relation.

The next invariant object is therefore the relation between maximal singular-value blocks.

## Canonical base

`b1dcd3ba818cae05897680d19c815bdc0943760b`

## Operator-defined invariant partition

Use only the scale-13 self-padded operator to define the partition. No outcome data enter block definition.

Maximal right-singular blocks are detected with tolerance

`abs(s_i-s_j) <= 1e-12 * max(1,abs(s_i),abs(s_j))`.

The frozen scale-13 partition is:

- block 0: modes {0,1,2,3}, dim 4
- block 1: {4}, dim 1
- block 2: {5}, dim 1
- block 3: {6}, dim 1
- block 4: {7,8,9,10,11}, dim 5
- block 5: {12,13,14,15,16}, dim 5
- block 6: {17}, dim 1
- block 7: {18,19,20,21,22}, dim 5
- block 8: {23}, dim 1
- block 9: {24,25,26,27}, dim 4
- block 10: {28,29}, dim 2
- block 11: {30}, dim 1

Each block is represented only by its orthogonal projector in centered input space.

This yields `C(12,2)=66` fixed block relations.

## Pilot exclusion

Seeds `127127..146146` were used only during implementation/design validation before this preregistration and are excluded from confirmatory inference.

## Fresh confirmatory seeds

`147147,148148,149149,150150,151151,152152,153153,154154,155155,156156,157157,158158,159159,160160,161161,162162,163163,164164,165165,166166`.

Exactly 20 independent fresh replicates.

## Same relation evaluated across scale

For every scale-13-defined block projector pair `(P_a,P_b)`, apply the exact same two input-space projectors under both operators `B_7` and `B_13`.

For centered residual `r`:

`y_a = B_s P_a r`
`y_b = B_s P_b r`.

All other components remain native.

Evaluate actual binary capability under the four pair sign states:

`C_++`, `C_+-`, `C_-+`, `C_--`.

Define the exact balanced block-pair interaction:

`X_s(a,b) = (C_++ + C_-- - C_+- - C_-+)/4`.

Define the scale-selective relational change:

`D(a,b)=X_13(a,b)-X_7(a,b)`.

Positive D means that the same invariant input-space relation becomes more constructive, or less destructive, at scale 13.

## Primary familywise test

For each of the 66 fixed block pairs and each of the 20 fresh replicates, compute `D_r(a,b)`.

Observed studentized statistic:

`T(a,b)=mean(D_r)/(sd(D_r)/sqrt(20))`.

The familywise null is the exact paired scale-label/sign-flip null.

Enumerate all `2^20 = 1,048,576` sign patterns. For each pattern, multiply the complete 66-dimensional D vector of replicate r by the same sign for that replicate. This preserves correlation among the 66 relations.

For each null pattern record:

`T_max = max over all 66 block pairs of T_null(a,b)`.

Familywise adjusted one-sided p for observed pair j:

`p_FWER(j)=count(T_max >= T_observed(j))/2^20`.

No random Monte Carlo approximation and no absolute effect-size floor are used.

Primary classification:

- `INVARIANT_BLOCK_RELATIONS_DETECTED` if at least one pair has positive mean D and `p_FWER <= 0.05`;
- `NO_INVARIANT_BLOCK_RELATION_DETECTED` otherwise.

Alpha=0.05 is the only inferential cutoff.

## Preregistered diagnostics

These do not change the primary result.

1. Number of FWER-significant positive block relations.
2. Strongest 10 relations by observed T and adjusted p.
3. Relations whose mean interaction changes sign:
   - `X_7 < 0 < X_13`
   - or `X_13 < 0 < X_7`.
4. Native scale13-scale7 capability advantage on the same seeds.
5. For each block:
   - dimension;
   - singular value;
   - target residual-energy overlap;
   - operator gain `||B_s P||_F^2` at both scales.
6. Relational-network concentration:
   - fraction of total positive D mass carried by top 1, top 3, top 5 pairs;
   - descriptive only.
7. Basis-invariance:
   rotate every degenerate block internally with 100 deterministic Haar rotations and verify every block projector and every D(a,b) remain unchanged within 1e-12.

## Integrity

Only validity failures yield `INSUFFICIENT_EVIDENCE`:

- block partition mismatch;
- projector symmetry/idempotence error >1e-12;
- pair coverage !=66;
- fresh replicate coverage !=20;
- internal-basis invariance error >1e-12;
- exact sign-pattern count !=1,048,576.

## Interpretation boundary

A positive result supports:

> one or more basis-invariant relations between operator-defined spectral blocks change their functional contribution with operating scale.

It does not establish a universal law, nor that the detected pair alone causes the full scale-13 capability advantage.

No pair selection, alpha change, or effect-size thresholding after outcome inspection is permitted.
