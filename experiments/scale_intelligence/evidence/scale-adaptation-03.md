# SCALE-ADAPTATION-03 result

Outcome: `NOT_FALSIFIED_BY_DATA`.

Canonical base: `e8279cb046ddcac4d39949e3401b9940279f3103`.

Preregistration commit: `627b6b45bb168b7d16208e5adc272ff996f51b1d`.

Single enabler tested:

```text
temporal state carryover + exact observed input delta
```

No extra channel, node, edge, fanout, round, model, task hint or global summary was introduced. The same scale sweep `1, 2, 4, 8, 16` and the same canonical substrate hashes were retained.

Confirmatory seeds: `1001, 2002, 3003`.

Episodes: `5 scales × 3 paired replicates × 256 counterfactual episodes`.

## Frozen-gate result

```text
baseline mean ceiling <= 0.10       PASS   observed 0.0404473
mean paired gain >= 0.02            PASS   observed 0.0364997
positive gain at >= 4/5 scales      PASS   observed 5/5
>= 3 paired replicates per scale    PASS   observed 3
non-enabler invariants identical    PASS
```

Baseline mean counterfactual adaptation: `0.0404473`.

Temporal-carryover mean: `0.0769469`.

Absolute paired gain: `+0.0364997`.

This is about a 90% relative increase over the baseline, but absolute adaptation remains low. The result therefore supports an enabler effect, not a solved adaptation mechanism.

## By scale

```text
scale   baseline    carryover   gain
1       0.0381531   0.0745288   +0.0363757
2       0.0419560   0.0770089   +0.0350529
4       0.0435475   0.0800058   +0.0364583
8       0.0390005   0.0760169   +0.0370164
16      0.0395792   0.0771743   +0.0375951
```

The enabled scale spread is only `0.0054770` and the gain spread is `0.0025422`. Diagnostic interpretation: the carryover effect is highly consistent across the tested scales and does not show the scale-8 peak seen for integration/transfer in SCALE-SEPARATION-02.

That diagnostic is not a frozen gate. It does not alter the primary outcome.

## Interpretation

Within this toy substrate, scale and temporal adaptation separate again:

- interaction scale materially changes integration/transfer;
- temporal carryover materially changes counterfactual adaptation;
- the carryover benefit is approximately scale-independent over the tested range.

This is consistent with the narrower architecture hypothesis that different capabilities can require different structural enablers rather than emerging from one scalar notion of "more connectivity" or "larger scale".

## Claim boundary

Supported only:

```text
On this fixed toy substrate, retaining prior evolved state and injecting the exact local input delta causally improves the preregistered counterfactual-adaptation metric relative to independent recomputation.
```

Not supported:

```text
that adaptation is solved;
that scale causes adaptation;
that this generalizes beyond this substrate;
that the result establishes intelligence, consciousness or biological equivalence.
```

Harness validation: `7 passed in 0.08s` locally. CPU-only.

Canonical machine-readable evidence: `evidence/scale-adaptation-03-result.json`.
