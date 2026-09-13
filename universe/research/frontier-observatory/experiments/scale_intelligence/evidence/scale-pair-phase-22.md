# SCALE-PAIR-PHASE-22 — result

Status: `PAIR_PHASE_OUTLIER_AGAINST_NULL`.

Canonical base: `420ca42768d3fd9d638681c70a52f815fd26ef66`  
Preregistration: `cf30b772c04278b9b9e18c0a2380be72d9a9f7cc`

## Direct balanced pair-phase intervention

For every pair, all non-pair modes remained native.

The two target modes were evaluated in all four flip states:

`C++`, `C+-`, `C-+`, `C--`.

The direct relative-phase contrast was:

`P_jk = (C++ + C--)/2 - (C+- + C-+)/2`.

This algebraically balances the two individual mode main effects and isolates concordant-versus-discordant relative phase.

The preregistered scale-selective effect was:

`DeltaP_jk = P_jk(scale13) - P_jk(scale7)`.

No absolute effect-size gate was used.

## Fixed target pair (6,7)

Fresh target DeltaP by replicate:

- `0.0072455`
- `0.0053868`
- `0.0046623`
- `0.0025202`
- `0.0070880`
- `0.0054498`
- `0.0077180`
- `0.0037802`
- `0.0057334`
- `0.0055129`

Mean:

`0.0055097`.

Positive in `10/10` fresh replicates.

Bootstrap 95% CI:

`[0.004546, 0.006414]`.

## Sign reversal across scale

Mean direct phase contrast for pair (6,7):

- scale 7: `P = -0.0030116`
- scale 13: `P = +0.0024981`

Thus the same pair relation is net destructive at scale 7 and net constructive at scale 13 under the balanced pair intervention.

The observed DeltaP is their difference:

`+0.0055097`.

## Exact pair-label null

All 465 unordered pairs were evaluated identically on the same fresh data.

Pair (6,7) fresh rank:

`#4 / 465`.

Only three other pairs had mean DeltaP >= the fixed target pair.

The preregistered one-sided exact pair-label p-value is:

`p = (1 + 3) / 465 = 0.00860215`.

At alpha=0.05:

`PAIR_PHASE_OUTLIER_AGAINST_NULL`.

No minimum effect magnitude entered the classification.

Fresh top pairs:

1. (0,2): `0.0058783`
2. (1,4): `0.0056830`
3. (2,4): `0.0056672`
4. (6,7): `0.0055097`
5. (2,13): `0.0050403`

## Native relevance context

Native self-padded segmented-block-13 capability:

- scale 7 mean: `0.792692`
- scale 13 mean: `0.828591`
- mean native advantage: `+0.035900`

Bootstrap 95% CI for native advantage:

`[0.032989, 0.039037]`.

The native advantage was context only, not a materiality gate.

## Interpretation

The prospectively fixed pair (6,7) survives a direct balanced relative-phase intervention and is an outlier against the full 465-pair null on new data.

The strongest new observation is the sign reversal:

> the same pairwise relation is destructive at scale 7 and constructive at scale 13.

That is stronger mechanistic information than a simple positive association. It says the functional contribution of a relation depends on the operating scale/context in which it is embedded.

This does not show that pair (6,7) alone is necessary for the entire scale-13 advantage. The pair contributes one part of a broader interaction structure.

The next mechanistic question is therefore not simply which pair matters, but what changes between scale 7 and 13 that rotates the same pair from destructive to constructive.

## Validation

- 465 unordered mode pairs;
- 10 completely fresh replicates;
- exact four-state capability contrast per pair and scale;
- 512 episodes per replicate;
- max numerical reconstruction error: `1.03e-14`;
- local vectorized CPU execution: ~`3.1 s`;
- no model/API calls.
