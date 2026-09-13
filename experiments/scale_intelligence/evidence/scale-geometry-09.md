# SCALE-GEOMETRY-09 — canonical result

Status: `FALSIFIED_BY_DATA`.

Preregistration: `9dc82306d3515405cf662c0fd9f1640da20710e9`.

Canonical base: `15f04e58869b006cc16e8395181eafe3b0e2b40a`.

## Run

- task blocks: `5, 9, 13`;
- interaction scales: `1, 2, 4, 8, 16`;
- fresh seeds: `27027, 28028, 29029, 30030, 31031`;
- 256 episodes per probe stream;
- 75 geometry × scale × replicate cells;
- same 63-node ring, 3 rounds, fanout 4, update rule, noise rate and non-geometry invariant digests;
- CPU-only local mirror; no model/API calls;
- full-trial canonical digest: `sha256:340153c7f83c7e60076fe02c9ab5e6b59d20edc85aed7ca080300f611d63d50a`.

## Aggregate curves

### Block 5

| scale | information efficiency | capability |
|---:|---:|---:|
| 1 | 0.544366 | 0.626866 |
| 2 | 0.624882 | 0.666636 |
| 4 | 0.675584 | 0.717603 |
| 8 | 0.690094 | 0.736843 |
| 16 | 0.643747 | 0.692609 |

Fitted vertices:

- efficiency: log2 `2.637354`, scale `6.221896`;
- capability: log2 `2.706867`, scale `6.529022`.

### Block 9

| scale | information efficiency | capability |
|---:|---:|---:|
| 1 | 0.480763 | 0.653206 |
| 2 | 0.579359 | 0.672476 |
| 4 | 0.668522 | 0.738597 |
| 8 | 0.722647 | 0.808265 |
| 16 | 0.679704 | 0.753646 |

Fitted vertices:

- efficiency: log2 `3.190823`, scale `9.131317`;
- capability: log2 `3.633935`, scale `12.414336`.

### Block 13

| scale | information efficiency | capability |
|---:|---:|---:|
| 1 | 0.459528 | 0.683395 |
| 2 | 0.545881 | 0.686880 |
| 4 | 0.656990 | 0.762227 |
| 8 | 0.725601 | 0.837537 |
| 16 | 0.715359 | 0.818459 |

Fitted vertices:

- efficiency: log2 `4.053414`, scale `16.603485`;
- capability: log2 `8.521801`, scale `367.551146`.

The block-13 capability quadratic is shallow and places its formal vertex far outside the tested interval even though the observed discrete curve peaks at scale 8. Treat that vertex as a failed preregistered surrogate, not as evidence for a literal scale near 368.

## Frozen gates

Passed:

- all aggregate quadratics are concave;
- aggregate efficiency vertices increase with block size;
- aggregate capability vertices increase with block size;
- small-to-large shift exceeds `0.25` log2 units for both metrics.

Failed:

- all vertices must remain inside the tested interval;
- efficiency/capability vertices must remain aligned within `0.75` log2 units for every geometry;
- large-over-small efficiency vertex shift must be valid in at least 4/5 paired replicates: observed `2/5`;
- large-over-small capability vertex shift must be valid in at least 4/5 paired replicates: observed `0/5`.

Therefore the preregistered mechanism claim is falsified.

## Evidence boundary

The result does not support the claim that the current quadratic response model has demonstrated a predictable geometry-driven movement of the optimum.

It also does not show the opposite mechanism. The raw curves move in the predicted qualitative direction at the low/middle scales, but the block-13 curve is not well represented by a global quadratic over `1..16`; the fitted optimum leaves the observation window while the discrete winner remains scale 8.

The material next uncertainty is therefore localization of the peak, not another threshold. A discriminating follow-up would use a preregistered denser scale grid inside the ring's non-wrapped useful range and a nonparametric peak-location rule.

No threshold, geometry, polynomial degree or result was retuned after observation.
