# Work claim: Agent Risk Attestation

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: 82f2d5a71bad960a6add983641afc90ace4430d2
Branch: feat/agent-risk-attestation

Active delivery: encode an insurer-facing Agent Risk Attestation Framework as a non-authorizing assurance layer over existing governed authority, REHT/RACS decisions and execution evidence.

Owned files:
- src/valo_kernel/agent_risk_attestation.py
- tests/test_agent_risk_attestation.py
- docs/agent_risk_attestation_framework.md
- src/valo_kernel/__init__.py
- .workclaims/agent-risk-attestation.md

Dependencies:
- existing principal authority semantics / AuthorityStateReference
- existing deterministic canonical_digest helper
- external REHT/RACS/Gateway/Veritas evidence remains referenced, not reimplemented

Invariants:
- attestation creates no authority and cannot issue clearance
- insurance/coverage determination remains external to VALO
- missing, stale, mismatched or contradictory required evidence fails closed
- attestation binds the exact action, decision, effect and outcome evidence by digest/reference
- no direct effect path is introduced
