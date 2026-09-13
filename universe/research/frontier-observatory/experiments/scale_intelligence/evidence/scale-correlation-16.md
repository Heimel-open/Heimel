# SCALE-CORRELATION-16 — result

Status: `FALSIFIED_BY_DATA`.

Canonical base: `00ef323fe1e712ea3e139cc9c39b0224f2e9c8e2`
Preregistration: `7e14740f36429f48f8f93054f50febb7c27ef9db`

## Generator verification

The intended latent correlation-length intervention was successfully implemented and separated from nominal block width.

Mean recovered latent correlation lengths across the five fresh seeds:

| nominal block B | target L=8 | target L=11 | target L=14 |
|---:|---:|---:|---:|
| 3 | 8.16 | 11.07 | 14.22 |
| 6 | 7.77 | 10.59 | 14.10 |

Thus the falsification is not attributable to failure to create the preregistered latent correlation lengths.

## Capability result

Median capability peaks:

| boundary | B | L=8 | L=11 | L=14 |
|---|---:|---:|---:|---:|
| reflected | 3 | 13 | 14 | 12 |
| reflected | 6 | 12 | 13 | 12 |
| self_padded | 3 | 7 | 8 | 12 |
| self_padded | 6 | 9 | 9 | 6 |

Failed gates:

- `reflected_block_3_strict_corr_order`
- `reflected_block_6_strict_corr_order`
- `self_padded_block_6_strict_corr_order`
- `all_medians_within_two_of_correlation_length`
- `all_cells_replicate_support`
- `nominal_block_invariance`
- `boundary_robustness`

The only broad gate that survives is that 10/12 cells are numerically closer to L than to nominal B by the preregistered two-scale-unit margin. That is insufficient because the peak locations do not track L monotonically or robustly.

Boundary robustness is poor: only 1/6 B×L cells has reflected vs self-padded median peak difference <=1.

## Replicate peaks

Reflected:

- B3/L8: `[11, 13, 15, 11, 13]`
- B3/L11: `[13, 14, 11, 14, 15]`
- B3/L14: `[12, 12, 13, 11, 15]`
- B6/L8: `[12, 13, 12, 11, 12]`
- B6/L11: `[13, 13, 12, 15, 11]`
- B6/L14: `[15, 12, 12, 13, 12]`

Self-padded:

- B3/L8: `[6, 7, 9, 7, 6]`
- B3/L11: `[7, 7, 8, 9, 9]`
- B3/L14: `[12, 12, 12, 6, 6]`
- B6/L8: `[12, 7, 9, 9, 6]`
- B6/L11: `[12, 6, 9, 6, 9]`
- B6/L14: `[6, 12, 6, 6, 12]`

## Interpretation

SCALE-RATIO-15's near one-to-one `capability_peak ≈ block size` relationship does not generalize when nominal block width and latent Markov correlation length are separated.

Therefore neither nominal block size itself nor latent exponential correlation length itself is established as the mechanism.

What survives is narrower: the original segmented generator induced a task geometry whose capability optimum matched its block scale, but that match was generator-specific.

The next mechanistic target should be the spectral structure of the task relative to the interaction kernel rather than a single scalar correlation length.

## Validation

- canonical sweep: 720 boundary-condition cells × 256 episodes per probe stream;
- fresh paired seeds: `62062, 63063, 64064, 65065, 66066`;
- vectorized semantic mirror;
- scalar/vector evolution parity: exact max absolute difference `0.0` on canonical B=3, L=11, scale=11, seed=64064 sample under both boundary conditions;
- no model/API calls;
- trial digest: `sha256:45bf9fe585298837eddf76ebc01186e404b9dd1429ea1f9df2cf49ec467ec67b`;
- compact result digest: `sha256:83a8da9639f423f201e1dbec6a8764a5b4aa0fcf50c82fcdab8f703a646ab15b`.
