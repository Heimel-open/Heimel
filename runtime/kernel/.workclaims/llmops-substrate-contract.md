# Work claim: LLMOps Substrate Contract

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: 0b50c18bbcc59bf36e26a8613e33142b34f30764
Branch: feat/llmops-substrate-contract

Active delivery: encode production LLMOps controls as a deterministic Governed Workspace substrate contract without moving authorization, clearance, authority or external execution into the substrate.

Owned files:
- src/valo_kernel/llmops_substrate.py
- tests/test_llmops_substrate.py
- docs/llmops_substrate_contract_v1.md
- .workclaims/llmops-substrate-contract.md

Dependencies:
- existing canonical_digest helper
- existing Governed Workspace / fresh-state / REHT boundary remains authoritative for consequence-bearing actions
- external serving, observability and evaluation systems remain provider-neutral implementations

Invariants:
- LLMOps controls create no authority and cannot issue clearance
- prompt/model/dataset/config changes produce a new substrate digest; stale bindings cannot be treated as current
- shadow/canary/eval/drift controls validate production readiness, not execution permission
- cost/context/rate controls constrain runtime resources but do not replace REHT/RACS
- tracing supports deterministic boundary correlation; it does not claim token-by-token model reproducibility
- no direct effect path is introduced
