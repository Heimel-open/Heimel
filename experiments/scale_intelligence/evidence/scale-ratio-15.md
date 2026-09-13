# SCALE-RATIO-15 — result

Status: `NOT_FALSIFIED_BY_DATA`.

Canonical base: `01e598bbd5c42dcf710cc10eeb2ee5ca23449677`  
Preregistration: `27424f2fd742e621b3ba1acdd656e0a99a2914fd`

## Held-out design

No previously tested task block was reused. Held-out blocks were `6, 8, 10, 12, 14`, with scales `4..15` and fresh paired seeds `57057, 58058, 59059, 60060, 61061`.

The test reused the same central scoring window and both endpoint rules from the preceding boundary experiments.

## Capability result

Reflected-line median peaks:

| task block | capability peak | peak / block |
|---:|---:|---:|
| 6 | 6 | 1.000 |
| 8 | 8 | 1.000 |
| 10 | 10 | 1.000 |
| 12 | 12 | 1.000 |
| 14 | 14 | 1.000 |

Every reflected replicate hit the exact task block: 25/25 block-replicate peak locations.

Self-padded median peaks:

| task block | capability peak | peak / block |
|---:|---:|---:|
| 6 | 6 | 1.000 |
| 8 | 8 | 1.000 |
| 10 | 9 | 0.900 |
| 12 | 12 | 1.000 |
| 14 | 13 | 0.929 |

Self-padded median absolute error was `0.4` scale units. Every block had 5/5 replicate peaks within two scale units of its task block.

All preregistered gates passed, including strict ordering under both boundary conditions and boundary robustness on 5/5 held-out blocks.

## Efficiency diagnostic

Information-efficiency did not obey the same invariant.

Reflected efficiency medians: `6, 15, 11, 13, 13` for task blocks `6, 8, 10, 12, 14`.

Self-padded efficiency medians: `6, 6, 5, 6, 7`.

Thus capability remains tightly locked to task spatial scale while the measured efficiency optimum can move elsewhere.

## Execution validation

The full sweep contains 600 condition-cells at 256 episodes per probe stream. Execution used a vectorized semantic mirror of the scalar repo transition. A canonical parity check at block `10`, scale `10`, seed `59059` matched reflected and self-padded efficiency components to at most `1.11e-16` floating-point difference.

Synthetic evaluator tests: `6/6` passed.

Trial digest: `sha256:ccdd5c3e0feb3c79219b953ba60424636a7ffe41640bd4eda07da36bbc71cebb`.

Compact result digest: `sha256:087a2bb5362a8b294c6d167e6413cd676f702d6fd60f7c0b9d4e8aad25687fc1`.

## Evidence boundary

This supports the bounded claim that, on this toy substrate, the capability operating scale tracks held-out task spatial correlation scale with approximately unit ratio across two different endpoint rules.

It does not establish that literal block size is the causal variable. Block size currently determines several geometric properties simultaneously. The next hard intervention is to separate correlation length from nominal block size while keeping the target task otherwise fixed.
