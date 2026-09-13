# Work claim: GitSpawn / context acquisition effects v0

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: 0a8205f8a3c169eede7b7d8e50c4d66a950d5c32
Branch: security/gitspawn-context-effects-v0
Draft PR: #73

Active delivery: make transitive consequence classification explicit for context acquisition and add a deterministic GitSpawn-class adversarial test proving that an apparent read/inspect operation is denied when repository-controlled configuration can trigger code execution before trust or authorization.

Owned files:
- src/valo_kernel/context_effects.py
- tests/test_context_effects.py
- docs/context_effect_boundary_v0.md
- .workclaims/gitspawn-context-effects-v0.md

Dependencies:
- existing fail-closed Kernel conventions
- NO_DIRECT_EFFECT_PATH remains canonical
- REHT/Gateway remain the execution authorization and enforcement boundary

Invariants:
- NO_UNGOVERNED_CONTEXT_EFFECT_PATH
- capability classification follows possible consequence, not surface intent
- context acquisition cannot execute repository-controlled helpers before trust/admissibility is established
- unknown transitive effect potential fails closed
- an operation named READ/STATUS/DIFF/INSPECT is not considered effect-free solely from its label
