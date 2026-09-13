# Work claim: Execution Responsibility Binding

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: 5e940de435856d24827b7eb05f31a9400a8dbb81
Branch: feat/execution-responsibility-binding

Active delivery: make execution-time responsibility allocation provable as a deterministic first-class contract without making VALO a legal-liability adjudicator or moving authorization out of REHT/RACS.

Owned files:
- src/valo_kernel/contracts/responsibility.py
- src/valo_kernel/contracts/__init__.py
- tests/test_execution_responsibility_binding.py
- docs/execution_responsibility_binding_v1.md
- .workclaims/execution-responsibility-binding.md

Dependencies:
- canonical_digest
- existing Authority / Delegation / Purpose semantics
- fresh Authority State and state_root supplied upstream
- REHT authorization and RACS disposition already exist before the pre-effect responsibility seal
- PEP remains the only governed effect path; Veritas/evidence remains post-effect proof

Invariants:
- responsibility binding creates no authority and cannot issue authorization, clearance or disposition
- legal liability is never determined by this contract
- principal, authority source, state provider, authorization evaluator, disposition issuer, enforcement owner and execution provider are explicit before effect commit
- every responsibility assignment has an explicit basis reference
- the pre-effect binding is content-addressed and tamper-evident
- post-effect evidence cryptographically binds the effect/receipt to the exact pre-effect responsibility binding
- no direct effect path is introduced
