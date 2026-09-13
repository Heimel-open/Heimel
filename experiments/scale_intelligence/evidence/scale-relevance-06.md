# SCALE-RELEVANCE-06 result

Status: **FALSIFIED_BY_DATA**.

Preregistration: `feb2101f37704140fe15e1cddd90047fbcc6e458`.

## Result

Fresh seeds: `12012, 13013, 14014, 15015, 16016`.

The independently measured capability peak replicated again at scale 8:

| scale | capability | integration | task-relevant AUC | task-relevant margin |
|---:|---:|---:|---:|---:|
| 1 | 0.64335 | 0.46187 | 0.93779 | 0.49749 |
| 2 | 0.67199 | 0.59682 | 0.91938 | 0.35536 |
| 4 | 0.73321 | 0.73671 | 0.83587 | 0.19178 |
| 8 | 0.79910 | 0.83164 | 0.73448 | 0.08554 |
| 16 | 0.73633 | 0.75786 | 0.71943 | 0.11952 |

Scale 8 beat both extreme scales in capability in all `5/5` fresh paired replicates.

Task-relevant AUC at scale 8 also exceeded scale 16 in `5/5` paired replicates, but the aggregate advantage was only `0.01505`, below the frozen `0.03` gate.

The stronger failure is the margin: scale 8 retained less support-versus-counterevidence separation (`0.08554`) than scale 16 (`0.11952`). The preregistered requirement was that scale 8 exceed scale 16 by at least `0.01`.

Failed gates:

- `candidate_auc_over_scale_16`
- `candidate_margin_over_scale_16`

No metric or threshold was changed after execution.

## Interpretation

The proposed task-relevant-differentiation explanation is not supported. The capability peak at scale 8 does **not** coincide with stronger preservation of the local distinction between evidence that originally supports versus opposes the correct global target.

In fact, capability rises from scale 1 to scale 8 while both task-relevant AUC and the support/counterevidence margin fall sharply. On this majority-style toy task, higher capability is therefore compatible with substantial destruction of local evidence identity.

This does not weaken the replicated scale/capability effect. It narrows its likely mechanism: the useful regime may be performing **task-sufficient compression** rather than balancing integration against preservation of local distinctions. The scale-16 capability decline, despite a slightly larger local-evidence margin than scale 8, also argues against local-detail preservation as the missing explanation.

That compression account is diagnostic only here. Testing it requires a new preregistered protocol that measures retained decision-sufficient information separately from discarded local detail.

## Validation

- 6/6 logical falsifier cases passed locally.
- CPU-only execution.
- 5 scales × 5 fresh replicates.
- 256 episodes per task family.
- Existing substrate and invariant digests unchanged.
