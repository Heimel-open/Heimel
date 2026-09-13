# Work anchor — Staying Human governance-gate adoption

Status: ACTIVE
Owner: ChatGPT
Claimed: 2026-08-17

Repository: `nsolland/valo-reht`
Canonical base: `05a1b68d9a7c0b512d6715cd7781f934ddef1910`
Branch: `adopt/staying-human-governance-gate`
Draft PR: `#26`

Owned files for this delivery:
- `docs/HUMAN_GOVERNANCE_GATE_PROFILE_V1.md`
- `docs/adoption/STAYING_HUMAN_WITH_AI_GOVERNANCE_GATE.md`
- `src/valo_reht/execution_requirements.py`
- `tests/test_human_governance_gate_profile.py`
- `docs/work-anchors/2026-08-17-staying-human-governance-gate.md`

Scope:
- adopt Trigger -> Criteria -> Authorized Decider -> Escalation -> Record as the human/organizational governance-gate profile around REHT;
- require an explicit positive human-gate decision when the profile is selected; refusal, partial or unresolved review cannot satisfy the gate;
- keep human approval as evidence/condition only: it cannot create or substitute for execution authority;
- preserve existing REHT action binding, nonce binding, current authority and fail-closed semantics;
- document source-derived ideas separately from REHT-native extensions.

Dependencies: current EAR v1 gate contract only. No Kernel, RACS, Gateway or Veritas changes required.