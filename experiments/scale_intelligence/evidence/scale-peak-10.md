# SCALE-PEAK-10 — result

Status: `NOT_FALSIFIED_BY_DATA`.

Canonical base: `52758c999ca8d9d4bb1874d1a4db37165a75223c`  
Preregistration: `ec0ec6364dbe69bce910e846caaf926a9f96e64e`

## Frozen design

- task blocks: `5, 9, 13`
- dense interaction scales: every integer `4..15`
- fresh seeds: `32032, 33033, 34034, 35035, 36036`
- 256 episodes per probe stream
- same 63-node ring, update rule, 3 rounds, fanout 4, scalar state and non-geometry invariants
- no quadratic fit, smoothing or interpolation
- peak per replicate = exact observed argmax; exact ties use mean tied scale
- geometry-level peak = median of five replicate peak locations

## Result

Median peak locations:

| task block | information efficiency | capability |
|---:|---:|---:|
| 5 | 5 | 5 |
| 9 | 10 | 10 |
| 13 | 13 | 11 |

Replicate peak locations:

- efficiency block 5: `[5, 6, 5, 5, 6]`
- efficiency block 9: `[11, 10, 10, 10, 11]`
- efficiency block 13: `[10, 13, 13, 13, 10]`
- capability block 5: `[5, 6, 5, 5, 5]`
- capability block 9: `[10, 10, 10, 9, 9]`
- capability block 13: `[11, 13, 10, 14, 11]`

Paired outward movement from block 5 to block 13: `5/5` replicates for information efficiency and `5/5` for capability.

All preregistered empirical gates passed:

1. complete paired coverage and invariant identity;
2. all median peaks strictly inside scale grid;
3. efficiency median peaks strictly ordered `5 < 10 < 13`;
4. capability median peaks strictly ordered `5 < 10 < 11`;
5. small-to-large shift >= 2 for both metrics;
6. efficiency/capability median peaks within 2 scale units inside every geometry;
7. efficiency outward in >=4/5 paired replicates — observed `5/5`;
8. capability outward in >=4/5 paired replicates — observed `5/5`.

Eight synthetic evaluator cases passed in the local mirror. Canonical CPU-only execution completed in approximately 8 seconds; no model/API calls were used.

Full canonical result-object digest: `sha256:bc7e6cec01ce74f89e6597377c7d6a07acdbca86d4f526b14d71eeb730820b8b`.

## Evidence boundary

This supports the bounded mechanism claim that, on this fixed toy ring substrate, increasing task spatial correlation length moves the empirically observed operating optimum outward for both information efficiency and independent capability.

It does not establish a universal scaling law or a general law of intelligence. The strongest next test is substrate transfer: change topology while preregistering the same directional geometry-to-optimum relationship.