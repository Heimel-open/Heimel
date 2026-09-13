# SCALE-PAIRWISE-20 — Pairwise interference attribution

## Phase A — frozen discovery ranking

This phase uses only prior SCALE-INTERFERENCE-19 seeds:
`77077, 78078, 79079, 80080, 81081`.

Fixed phenomenon:
- boundary: self-padded
- task: segmented block 13
- scales contrasted: 7 and 13

For each scale, decompose central residual transfer exactly as in SCALE-MODES-18:
`B_s = U Sigma V^T`.

For every mode pair (j,k), with all other modes native, evaluate the four sign states (++,+-,-+,--). Ranking does NOT use binary capability. It uses the smooth target-aligned utility

`u(z) = -log(1 + exp(-z))`

on central decision margin z.

Pair interaction:
`I_jk = (u++ + u-- - u+- - u-+)/4`.

Discovery score:
`D_jk = mean(I_jk at scale13) - mean(I_jk at scale7)`.

Rank descending by D_jk. Freeze K=5 before ranking.

The union of modes appearing in the top-5 pairs becomes the targeted mode set.

A six-mode control set is selected from modes not in the targeted set by minimizing absolute difference in mean modal L2 energy, using the same discovery episodes and scales 7/13 only. Capability is not used for control matching.

Fresh confirmatory seeds are not generated or inspected until Phase B protocol, pair list, control set and gates are committed.
