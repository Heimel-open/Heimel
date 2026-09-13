# SCALE-RELEVANCE-06 — Task-relevant differentiation

Status before execution: PREREGISTERED.

## Question

SCALE-ORDER-05 falsified the explanation that the interior capability peak is caused by preserving the original local node pattern. The next bounded question is narrower:

> At the interior capability peak, does the final state preserve task-relevant distinctions between local evidence that supports versus opposes the correct global target better than the high-scale extreme does?

This is a toy-substrate test. It does not define human understanding, consciousness, or general intelligence.

## Prior evidence boundary

The scale/capability peak observed in earlier protocols is hypothesis-generating. No prior seed or result counts as confirmation here. SCALE-ORDER-05 remains negative and is not reinterpreted.

## Frozen substrate

Reuse `scale_sweep.py` unchanged:

- 63 nodes on the same distance-labelled ring;
- scales `1, 2, 4, 8, 16`;
- 3 synchronous rounds;
- fanout 4;
- one scalar state channel;
- same update rule and task generators;
- 256 episodes per family;
- same invariant digests.

Fresh replicate seeds: `12012, 13013, 14014, 15015, 16016`.

Only `interaction_scale` varies within a replicate.

## Frozen measurements

### Capability

`0.5 * (task_success + cross_context_transfer)` from the existing runner. Integration is excluded from capability.

### Task-relevant AUC

For each segmented episode:

1. compute the correct global target from the initial majority;
2. label each node as `support` if its initial sign supports that target or `counterevidence` if it opposes it;
3. align each final node state to the correct target by multiplying by the target sign;
4. compute the pairwise AUC: probability that a support node has a larger target-aligned final state than a counterevidence node; exact ties score `0.5`.

This asks whether the final representation still distinguishes evidence by its relevance to the task, not whether it preserves raw node identity.

### Task-relevant margin

Within each episode, compute:

`mean(target_aligned_final | support) - mean(target_aligned_final | counterevidence)`.

Divide by `2`, the maximum initial separation between the two signed evidence classes, and clip to `[0,1]`.

AUC measures recoverable ordering; the margin prevents an infinitesimal ranking signal from being treated as a strong surviving distinction.

### Integration

Existing `distributed_integration`, retained as diagnostic only.

## Preregistered gates

The candidate is the highest-capability scale among `2, 4, 8`.

The hypothesis survives only if all gates hold:

1. candidate capability exceeds scale 1 by at least `0.05`;
2. candidate capability exceeds scale 16 by at least `0.05`;
3. candidate task-relevant AUC is at least `0.60`;
4. candidate AUC exceeds scale 16 AUC by at least `0.03`;
5. candidate normalized task-relevant margin is at least `0.03`;
6. candidate normalized margin exceeds scale 16 by at least `0.01`;
7. candidate capability exceeds both extreme scales in at least `4/5` paired fresh replicates;
8. candidate task-relevant AUC exceeds scale 16 in at least `4/5` paired fresh replicates.

Five valid replicates are required at every scale. Any invariant drift yields `INSUFFICIENT_EVIDENCE`.

No metric, seed, gate, or threshold may be changed after execution.

## Interpretation

`NOT_FALSIFIED_BY_DATA` would support only the bounded claim that the interior capability regime on this fixed substrate preserves task-relevant evidence distinctions better than the high-scale extreme, despite SCALE-ORDER-05 showing that raw local-pattern preservation does not explain the peak.

`FALSIFIED_BY_DATA` means this task-relevant-differentiation explanation fails under the frozen metric and gates. It does not falsify the already replicated scale/capability effect itself.
