# SCALE-TOPOLOGY-11 — result

Status: `FALSIFIED_BY_DATA`.

Canonical base: `6062231d1ee95348cf3dd53aad576d80c925dbc3`  
Preregistration: `37082f170096e980c671d15395e5456a06772385`

## Frozen design

SCALE-PEAK-10 was transferred from the periodic 63-node ring to a non-periodic 63-node reflected line. All task/scoring machinery and the nonparametric peak evaluator were kept fixed.

- task blocks: `5, 9, 13`
- dense scales: every integer `4..15`
- fresh seeds: `37037, 38038, 39039, 40040, 41041`
- 256 episodes per probe stream
- 3 synchronous rounds
- four message slots plus self, same `/5` average
- reflected endpoint mapping instead of cyclic modulo wrap
- exact observed argmax per replicate; exact ties use mean tied scale
- geometry peak = median of five replicate peaks
- no smoothing, interpolation, fit, or post-outcome retuning

Topology fingerprint: `sha256:b8b63198804176ba8562bea90ec15cb69550fb3e6a339fca797cf1936f96d909`.

## Result

Median peak locations:

| task block | information efficiency | capability |
|---:|---:|---:|
| 5 | 7 | 12 |
| 9 | 11 | 9 |
| 13 | 13 | 13 |

Replicate peak locations:

- efficiency block 5: `[7, 13, 11, 5, 5]`
- efficiency block 9: `[13, 11, 9, 11, 11]`
- efficiency block 13: `[13, 14, 13, 13, 13]`
- capability block 5: `[9, 15, 12, 13, 5]`
- capability block 9: `[9, 9, 9, 9, 9]`
- capability block 13: `[13, 13, 13, 13, 13]`

Paired block-5 to block-13 outward movement:

- information efficiency: `5/5`
- capability: `3/5`

Preregistered gates:

- median peaks interior: PASS
- efficiency strict order `7 < 11 < 13`: PASS
- capability strict order `12 < 9 < 13`: FAIL
- minimum block-5 to block-13 shift >=2 for both metrics: FAIL because capability shifts only `+1`
- efficiency/capability median alignment <=2 within every geometry: FAIL because block 5 differs by `5`
- paired efficiency outward >=4/5: PASS (`5/5`)
- paired capability outward >=4/5: FAIL (`3/5`)

The canonical verdict is therefore `FALSIFIED_BY_DATA`. No threshold or peak rule was changed.

## Diagnostic boundary

The failure is concentrated in small-geometry capability localization on the reflected line. For block 5, the aggregate capability surface is shallow and multi-peaked: its aggregate maximum is at scale 5 (`0.72309`), but nearby scales 7, 9, 13 and 15 are close, and per-replicate exact argmax locations scatter across `[9, 15, 12, 13, 5]`. By contrast:

- block-9 capability peaks at scale 9 in `5/5` replicates;
- block-13 capability peaks at scale 13 in `5/5` replicates;
- information-efficiency medians remain strictly ordered `7 < 11 < 13` and move outward in `5/5` paired replicates.

This means the ring result does **not** transfer as the preregistered joint efficiency+capability mechanism claim. It does not establish that task geometry is irrelevant on the reflected line; one of the two independent observables retains the predicted ordering, while small-block capability peak identity becomes unstable under the topology change.

The material next uncertainty is therefore topology-induced peak identifiability/boundary effects, not a new threshold.

Canonical deterministic execution covered 180 geometry/scale/replicate cells and completed in approximately 53 seconds on CPU with no model/API calls. Four topology-specific mirror checks passed; the SCALE-PEAK-10 evaluator and its thresholds were reused unchanged.

Canonical trial digest: `sha256:d81a4472ba4c2392d7f91c355391015809f31e6ae9f1b7ef7c84975d98d607ec`  
Canonical full-result digest: `sha256:9efe9b3edb9d6c10b938b20939310dddb857b94c5bf3a20c2b4f7eb84e14c48c`

## Evidence boundary

SCALE-TOPOLOGY-11 falsifies the bounded claim that the complete SCALE-PEAK-10 geometry-to-optimum relationship transfers unchanged from the periodic ring to this reflected-line substrate.

It does not establish a universal topology dependence and does not isolate which reflected-line property causes the failure. Candidate causes remain boundary heterogeneity, duplicate reflected message targets near the ends, or genuine topology sensitivity. Those require new preregistered interventions.