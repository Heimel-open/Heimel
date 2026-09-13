# SCALE-CROSSPROJECTOR-25 — Basis-invariant relational cross-term

Status before fresh execution: PREREGISTERED.

## Question

Does the scale-13 capability advantage depend on a basis-invariant nonlinear interaction between the implicated invariant target subspace and the rest of the centered system?

This follows SCALE-PROJECTOR-24, which showed that the whole target subspace is not an unusually strong gross causal carrier.

## Canonical base

`25c79cd05b662d44ea6a919fdd47aede5d2e5fd7`

## Operator-only preflight correction

For the fixed projectors, operator gain is

`g_s(P)=||B_s P||_F^2`.

Target gains:

- scale 7 target block {6,7,8}: approximately `0.330608`;
- scale 13 target block {7,8,9,10,11}: approximately `2.021343`.

These are higher than the mean gain of uniform dimension-matched random subspaces, not lower.

Therefore the SCALE-PROJECTOR-24 null was not made artificially strong by larger average random operator gain. Gain remains a diagnostic confound, but it is not the next primary question.

## Fixed target projectors

Self-padded segmented block 13.

- scale 7: projector onto exact degenerate right-singular block {6,7,8}, dimension 3;
- scale 13: projector onto exact degenerate right-singular block {7,8,9,10,11}, dimension 5.

Let `Q` be the centered-space projector and `P_s` the target projector.

Fresh seeds:

`117117,118118,119119,120120,121121,122122,123123,124124,125125,126126`.

## Basis-invariant decomposition

For centered residual `r`:

`y_T = B_s P_s r`

`y_R = B_s (Q-P_s) r`.

Then native centered output is exactly

`y_T + y_R`.

The global/DC majority contribution remains unchanged.

## Four-state relational intervention

Flip target and remainder contributions independently with
`a,b in {-1,+1}`.

Evaluate actual binary central capability:

`C_ab = capability(mu + a*y_T + b*y_R)`.

Define the exact balanced cross-term:

`X_s = (C_++ + C_-- - C_+- - C_-+)/4`.

The main effect of flipping either component alone cancels algebraically. X isolates the nonlinear capability interaction between the invariant target subspace and its complement.

Primary scale-selective statistic:

`DeltaX_target = X_13 - X_7`.

Positive DeltaX means the target-vs-rest relation becomes more constructive at scale 13 relative to scale 7.

## Dimension-matched random-projector null

Generate exactly 1,000 deterministic Haar-random centered projectors at each scale:

- rank 3 at scale 7;
- rank 5 at scale 13.

Use NumPy PCG64 seed `250025`, paired by draw index.

For each random projector `R_s`, decompose identically into

`B_s R_s r` and `B_s(Q-R_s)r`

and compute `DeltaX_q`.

Primary one-sided empirical p:

`p = (1 + count(DeltaX_q >= DeltaX_target)) / 1001`.

No absolute effect-size floor is imposed.

Classification:

- `CROSSPROJECTOR_OUTLIER_AGAINST_NULL` if DeltaX_target > 0 and p <= 0.05;
- `NOT_CROSSPROJECTOR_OUTLIER_AGAINST_NULL` otherwise.

Alpha=0.05 is the only primary inferential cutoff.

## Preregistered diagnostics

These do not alter the primary classification.

1. Report target `X_7`, `X_13`, and whether their signs differ.
2. Report target `DeltaX` by fresh replicate and bootstrap 95% CI.
3. Report operator gains `||B_s P_s||_F^2` for target and all random projectors.
4. Report Spearman correlation between random-projector gain and `DeltaX_q`.
5. Gain-nearest diagnostic:
   - define paired log-gain distance
     `d_q=sqrt(log(g7_q/g7_target)^2 + log(g13_q/g13_target)^2)`;
   - select the 100 smallest d_q before looking at their DeltaX ranks;
   - report target rank and empirical p within these 100 nearest-gain draws plus target;
   - no maximum acceptable gain distance is imposed, so this is descriptive only.
6. Report native scale13-scale7 capability advantage as context.

## Integrity

Only validity failures yield `INSUFFICIENT_EVIDENCE`:

- projector symmetry/idempotence error >1e-12;
- target+complement decomposition error >1e-12;
- projector change under internal degenerate-basis rotation >1e-12;
- incomplete 10-seed coverage;
- null draw count/RNG mismatch.

## Interpretation boundary

A positive result supports:

> capability depends on a basis-invariant nonlinear relation between an invariant subspace and the rest of the system, and that relation changes with operating scale.

It would not establish a universal law or identify the microscopic interaction inside the subspaces.

No outcome-dependent projector selection, alpha change, or effect-size thresholding is permitted.
