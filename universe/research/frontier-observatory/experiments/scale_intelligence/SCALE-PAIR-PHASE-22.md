# SCALE-PAIR-PHASE-22 — Direct pair-phase intervention

Status before fresh execution: PREREGISTERED.

## Question

Does the prospectively identified pair (6,7) carry unusually strong direct relative-phase/interference effect on the self-padded segmented-block-13 scale-13 advantage?

This protocol removes arbitrary absolute effect-size gates.

## Canonical base

`420ca42768d3fd9d638681c70a52f815fd26ef66`

## Fixed target

Target pair: `(6,7)`.

Fixed phenomenon:

- self-padded boundary;
- segmented block 13;
- scale contrast 13 vs 7;
- central scoring nodes 16..46.

Fresh seeds:

`97097, 98098, 99099, 100100, 101101, 102102, 103103, 104104, 105105, 106106`.

## Pair intervention

For each unordered mode pair (j,k), all non-pair modes remain native.

Let pair flip variables `a,b in {-1,+1}` multiply the native modal coefficients of modes j and k.

Evaluate actual binary central capability in the four states:

`C++`, `C+-`, `C-+`, `C--`.

Define balanced relative-phase contrast:

`P_jk = (C++ + C--)/2 - (C+- + C-+)/2`.

Each individual mode is positive in half the terms and negative in half the terms, so single-mode main effects cancel algebraically. P isolates the concordant-versus-discordant relative-phase interaction for the pair, conditional on all other modes remaining native.

Define scale-selective direct phase effect:

`DeltaP_jk = P_jk(scale13) - P_jk(scale7)`.

## Primary statistic

`T = mean_r DeltaP_(6,7)` across 10 fresh replicates.

## Pair-label null

Compute fresh mean DeltaP for all 465 unordered pairs under the identical intervention.

One-sided exact empirical p:

`p = (1 + count(other pairs with mean DeltaP >= target mean DeltaP)) / 465`.

No absolute effect-size floor is imposed.

Classification:

- `PAIR_PHASE_OUTLIER_AGAINST_NULL` if target mean DeltaP > 0 and p <= 0.05;
- `NOT_PAIR_PHASE_OUTLIER_AGAINST_NULL` otherwise.

Alpha=0.05 is the only inferential cutoff.

## Diagnostics

Report:

- 10 target DeltaP replicate values;
- bootstrap 95% CI of target mean;
- positive replicate count;
- native scale13-scale7 capability advantage on the same fresh seeds;
- fresh rank of pair (6,7) among all 465 pairs.

These do not alter the primary classification.

## Integrity

Only validity failures yield `INSUFFICIENT_EVIDENCE`:

- incomplete 465-pair x 10-replicate coverage;
- duplicate pairs;
- seed mismatch;
- SVD/state/modal reconstruction error >1e-12.

## Interpretation boundary

A positive result supports only that the prospectively fixed pair (6,7) has an unusually strong direct concordant-versus-discordant phase effect at scale13 relative to scale7 compared with identically constructed interventions across the full pair space.

It does not establish that pair (6,7) alone is necessary for the entire scale13 advantage.

No pair substitution, alpha change, or outcome-dependent thresholding is permitted.
