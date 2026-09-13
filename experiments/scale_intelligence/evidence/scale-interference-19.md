# SCALE-INTERFERENCE-19 — result

Status: `NOT_FALSIFIED_BY_DATA`.

Canonical base: `9210f5871c6040d4158112f95a2ed5ebae4dbcef`  
Preregistration: `fef3df4ea98e70d606c5c99ea0a3384c6c23e9c1`

## Frozen causal intervention

For every episode, scale and boundary condition, the native SVD residual coefficients were independently sign-scrambled 16 times:

`c_j -> epsilon_j c_j`, with `epsilon_j ∈ {-1,+1}`.

The intervention preserved:

- all singular values;
- all modal coefficient magnitudes;
- every per-mode L2 energy;
- total central residual L2 power;
- the global/DC majority signal.

It changed only relative modal signs/phases and therefore local cancellation/reinforcement.

Maximum observed residual-power preservation error:

`2.49e-14` (gate: <= `1e-12`).

Maximum numerical reconstruction error:

`1.53e-14` (gate: <= `1e-12`).

## Primary fixed cell

Self-padded segmented block 13, fixed contrast scale 13 vs scale 7.

Fresh native capability advantage by replicate:

- `+0.03667`
- `+0.03547`
- `+0.03541`
- `+0.03446`
- `+0.03768`

Mean native advantage:

`+0.03594` (required >= `+0.020`).

Positive in `5/5` replicates.

After modal sign scrambling, scale-13 vs scale-7 advantage by replicate:

- `+0.00090`
- `-0.00158`
- `+0.00621`
- `+0.00592`
- `+0.00821`

Mean scrambled advantage:

`+0.00393` (required absolute <= `0.010`).

Thus mean causal collapse of the scale-13 advantage was:

`0.03594 - 0.00393 = 0.03200`.

Required: >= `0.015`.

Collapse by replicate:

- `0.03577`
- `0.03705`
- `0.02919`
- `0.02854`
- `0.02947`

All `5/5` exceed the preregistered `0.010` replicate floor.

## Specificity control

At the independently fixed neighboring control peaks:

- self-padded seg_b7 / scale7 scrambling effect:
  `native - scrambled = -0.00266`;
- self-padded seg_b10 / scale9:
  `+0.00347`.

Mean absolute control effect:

`0.00307`.

At the primary self-padded seg_b13 / scale13 cell:

`native - scrambled = +0.02067`.

Specificity gap:

`0.02067 - 0.00307 = 0.01760`.

Required: >= `0.008`.

## Key curve

Self-padded segmented block 13:

| scale | native capability | scrambled capability | native - scrambled |
|---:|---:|---:|---:|
| 4 | 0.75285 | 0.75648 | -0.00363 |
| 5 | 0.77419 | 0.77437 | -0.00018 |
| 6 | 0.78754 | 0.79335 | -0.00581 |
| 7 | 0.79322 | 0.80456 | -0.01134 |
| 8 | 0.79714 | 0.80063 | -0.00349 |
| 9 | 0.79582 | 0.79873 | -0.00292 |
| 10 | 0.78661 | 0.79623 | -0.00962 |
| 11 | 0.79916 | 0.79919 | -0.00004 |
| 12 | 0.82135 | 0.80260 | +0.01874 |
| 13 | 0.82916 | 0.80849 | +0.02067 |
| 14 | 0.78793 | 0.78938 | -0.00146 |
| 15 | 0.75779 | 0.77722 | -0.01943 |

The important causal pattern is not merely a generic degradation under scrambling.

At scale 7, scrambling improves capability by about 1.13 percentage points.  
At scale 13, scrambling reduces capability by about 2.07 points.

Therefore the native relative modal arrangement specifically creates the scale-13 advantage over scale 7.

## Gates

All preregistered gates passed:

- numerical reconstruction;
- scramble energy preservation;
- fresh native scale13-over-scale7 advantage >=0.020;
- native advantage positive in >=4/5;
- scrambled advantage absolute <=0.010;
- aggregate collapse >=0.015;
- collapse >=0.010 in >=4/5;
- specificity gap >=0.008.

## Interpretation

This is the first direct causal result in the sequence that preserves the modal amplitudes and total residual energy while perturbing only their relative sign/phase structure.

On this fixed toy substrate:

> the self-padded segmented-block-13 scale-13 capability advantage depends on the native interference/cancellation pattern among residual transfer modes.

This does not yet identify which mode pairs create the effect. The next hard test is pairwise attribution: selectively flip or remove mode pairs and identify the interactions whose joint contribution produces the scale-13 advantage.

## Validation

- canonical cells: `1080`;
- 16 independent deterministic sign scrambles per trial;
- 512 episodes per task/replicate;
- fresh seeds: `77077, 78078, 79079, 80080, 81081`;
- local vectorized CPU run: ~`13.95 s`;
- no model/API calls;
- trial digest: `sha256:245efed313c7cf617e4921c0ae9da28aa846b50d153fb3f1a546357417e331a9`;
- compact result digest: `sha256:1091d6155b1e4bf1cfa95507d93f1ff0a7565665a80a26e32a9e4590d4f9381e`.
