# SCALE-ORDER-05 evidence — negative result

Status: `FALSIFIED_BY_DATA`.

Preregistration commit: `71c319d31c7a38fc6a4798ef79a4cf43fc9d11bb`.

No gate or metric was changed after observation.

## Result

Independent capability again peaks at interaction scale 8:

| scale | integration | differentiation | capability | balance |
|---:|---:|---:|---:|---:|
| 1 | 0.46377 | 0.49891 | 0.64484 | 0.48060 |
| 2 | 0.60099 | 0.35139 | 0.67639 | 0.44333 |
| 4 | 0.74023 | 0.18724 | 0.73955 | 0.29876 |
| 8 | 0.83333 | 0.08317 | 0.80351 | 0.15124 |
| 16 | 0.75227 | 0.12333 | 0.74364 | 0.21186 |

The capability peak is robust across all five fresh replicates: scale 8 beats both extreme scales in `5/5` paired replicates.

Three preregistered gates survive:

- scale-8 capability exceeds scale 1 by `+0.15867`;
- scale-8 capability exceeds scale 16 by `+0.05986`;
- scale-8 integration exceeds scale 1 by `+0.36956`.

Two critical gates fail:

1. scale-8 differentiation is **lower**, not higher, than scale-16 differentiation (`0.08317` vs `0.12333`; gap `-0.04016`);
2. scale 8 is far outside the preregistered integration–differentiation balance zone. Its balance is `0.15124`, while the maximum balance occurs at scale 1 (`0.48060`), giving a balance gap of `0.32937` versus the allowed `0.02`.

Therefore the proposed account — that capability peaks because the substrate sits between insufficient integration and loss of preserved local distinctions as measured here — is falsified on this substrate/range.

## What survived

The earlier scale result survives independently: capability has a strong interior peak around scale 8 under fixed substrate, bandwidth and compute.

What failed is the proposed explanation for that peak.

The frozen differentiation instrument measures preservation of the *original local state pattern*. Capability improves while that quantity falls sharply. This means one of two things must remain open:

- preserved raw/local distinctions are not the differentiation relevant to the task; or
- the interior capability peak is produced by a mechanism that is not an integration–differentiation balance of the preregistered kind.

Neither possibility may be selected as the explanation from this run alone.

## Important boundary

Do not rescue SCALE-ORDER-05 by redefining differentiation after seeing the result.

A follow-up may test a new, preregistered concept of **task-relevant differentiation**: whether distinct information classes remain discriminable after integration, rather than whether the final state resembles the original node-by-node local pattern. That is a new hypothesis and must receive a new protocol number.

This result does not define or measure human understanding, consciousness, or general intelligence.
