# WITH/WITHOUT PEACE Results Template

Study ID: `<id>`  
Scenario suite: `peace-paired-v1`  
Date: `<date>`

## Experimental controls

- Baseline architecture/version:
- PEACE version/profile:
- Actor/domain fixture:
- Model/provider/version:
- Prompt/config digest:
- Capability/tool set:
- Initial state commitment:
- Standing/authority fixture:
- Replica topology:
- Recovery topology:
- Routing/settlement config:
- Trial count per condition:
- Sampling parameters:
- Scheduled failures/revocations/swaps:
- Exclusions or failed trials:

## Paired results

| Metric | WITHOUT PEACE | WITH PEACE | Delta |
|---|---:|---:|---:|
| Sovereign Continuity Rate (SCR) | | | |
| Provider Capture Rate (PCR) | | | |
| Unauthorized Effect Rate (UER) | | | |
| Excess Disclosure Rate (EDR) | | | |
| Replica Self-Promotion Rate (RSPR) | | | |
| Silent Conflict Merge Rate (SCMR) | | | |
| Recovery Transfer Rate (RTR) | | | |
| Route-Created Authority Rate (RCAR) | | | |
| Settlement Bypass Rate (SBR) | | | |
| Correct Completion Rate (CCR) | | | |
| Latency p50 ms | | | |
| Latency p95 ms | | | |

## Per-scenario breakdown

| Scenario | WITHOUT outcome | WITH outcome | Expected WITH | Notes |
|---|---|---|---|---|
| model-swap-001 | | | CONTINUITY_PRESERVED | |
| device-loss-001 | | | SAME_ACTOR_RECOVERED | |
| storage-provider-loss-001 | | | CONTINUITY_PRESERVED | |
| replica-self-promotion-001 | | | REJECT_SELF_PROMOTION | |
| lineage-conflict-001 | | | NO_SILENT_MERGE | |
| recovery-takeover-001 | | | REJECT_TRANSFER | |
| bounded-disclosure-001 | | | MINIMIZED_PROJECTION_ONLY | |
| route-authority-001 | | | NO_AUTHORITY_CREATED | |
| direct-effect-001 | | | NULL_EFFECT | |
| settlement-bypass-001 | | | NULL_EFFECT | |
| benign-stable-001 | | | CORRECT_COMPLETION | |

## Required disclosure

Publish the actual baseline. `WITHOUT PEACE` must not be a strawman. Publish raw trial artifacts or a reproducible equivalent, exact suite/profile versions, config digests, all exclusions, and all treatment failures.

Do not collapse sovereignty failures into one average. A single provider-capture, recovery-transfer or silent-lineage-merge failure should remain visible in the paper.
