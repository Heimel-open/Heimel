# SCALE-BOUNDARY-DYNAMICS-13 — result

Formal status: `INSUFFICIENT_EVIDENCE`.

Canonical base: `99a75b22f3de4239fef380ca2e82bc441f504654`  
Preregistration: `3253fdaca235ba049ecdbead31b99a0b55c69b24`

## Frozen intervention

Only endpoint address resolution changed:

- `reflected`: mirror out-of-range message addresses;
- `self_padded`: out-of-range message slots resolve to the receiving node.

Everything else remained fixed: 63 nodes, task blocks 5/9/13, scales 4..15, 3 rounds, four message slots, /5 normalizer, task generation, paired fresh episodes, and central scoring on nodes 16..46.

Fresh seeds: `47047, 48048, 49049, 50050, 51051`.

## Result

### Reflected condition

The complete SCALE-PEAK-10 relation replicated:

| block | efficiency peak | capability peak |
|---:|---:|---:|
| 5 | 5 | 5 |
| 9 | 9 | 9 |
| 13 | 13 | 13 |

All frozen peak gates passed.

### Self-padded condition

Capability retained the same ordered peaks:

| block | capability peak |
|---:|---:|
| 5 | 5 |
| 9 | 9 |
| 13 | 13 |

But information-efficiency did not:

| block | efficiency peak |
|---:|---:|
| 5 | 5 |
| 9 | 5 |
| 13 | 6 |

The self-padded condition therefore failed:

- `efficiency_strict_order`;
- `minimum_small_large_shift`;
- `within_geometry_alignment`.

Because the preregistration required both boundary conditions to preserve the complete geometry relation before the primary causal peak-shift comparison was admissible, the formal result is `INSUFFICIENT_EVIDENCE`, reason `condition_geometry_relation_failed`.

## Primary endpoint — descriptive only

The preregistered primary endpoint was block-5 capability peak.

- reflected replicate peaks: `[5,5,5,5,5]`;
- self-padded replicate peaks: `[5,5,5,5,5]`;
- paired deltas: `[0,0,0,0,0]`;
- median shift: `0`.

This cannot be promoted to the formal falsification verdict because the self-padded prerequisite relation failed.

## Material diagnostic

The intervention sharply decoupled the two previously aligned observables:

`capability peaks: 5 -> 9 -> 13`

while

`information-efficiency peaks: 5 -> 5 -> 6`.

Since episodes, central scoring, compute, task geometry and scale grid were paired and fixed, the boundary rule itself is sufficient on this toy substrate to alter the information-efficiency response surface without comparably moving the capability peak locations.

This is a diagnostic causal observation, not the preregistered primary claim.

## Validation

- synthetic evaluator cases: `6/6` passed;
- canonical run: 360 condition-cells, 256 episodes per probe stream, approximately 44 s CPU;
- no model/API calls;
- trial digest: `sha256:2f2eef9c49a6afe18b675c91d349b90c6898b5d11ca3ec0e05fb33639285ac97`;
- full result digest: `sha256:0fefc0ceb8405820faa7742d7504a4de26eb1c4754ae1b03b2d76a90130ff64e`.

## Evidence boundary

SCALE-BOUNDARY-DYNAMICS-13 does not establish that endpoint rules materially move the block-5 capability optimum.

It does establish a new material uncertainty: the information-efficiency optimum can be strongly moved by the boundary rule while the capability peak ordering remains nearly unchanged. That directly challenges treating the two curves as the same mechanism without a further causal test.
