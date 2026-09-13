# Work claim: Verification Proof Contract

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: ddab7e6fedfcc7ed4e9958c1ef09045cf537dc02
Branch: feat/verification-proof-contract
Draft PR: #48

Active delivery: adopt provider- and domain-neutral independent verification, explicit refusal-as-success semantics, deterministic boundary regeneration, immutable definition binding, and per-step proof anchors without moving authorization or execution into Kernel.

Owned files:
- src/valo_kernel/contracts/verification_proof.py
- tests/test_verification_proof.py
- docs/verification_proof_contract_v1.md
- src/valo_kernel/contracts/__init__.py
- .workclaims/2026-08-17-verification-proof-contract.md

Dependencies:
- canonical digest semantics remain authoritative
- Evidence admission and governed WorldState remain unchanged
- burden/replay contracts remain the reconstruction layer
- fresh REHT authorization, deterministic RACS disposition, PEP/Gateway enforcement, and Veritas effect evidence remain separate boundaries

Invariants:
- verification evidence never creates authority or clearance
- a verification claim must bind an immutable definition digest and exact subject/version
- independent checks distinguish reference/closed-form, independent-route/cross-model, and expected-refusal controls
- expected refusal is a positive verification result only when the tested invalid case is actually refused
- successful positive checks require evidence; failed checks require reason codes
- proof completeness fails closed when required checks are absent, failed, or structurally invalid
- deterministic regeneration compares reproduction digests over pinned semantic inputs and outputs; token-by-token model replay is out of scope
- multi-step proofs preserve per-step anchors and ordered chain binding
- no direct effect path is introduced

Source note:
- external convergence observed in DASE Capability Console — Proof of Capability (2026): independent reference checks, cross-model verification, built-to-fail refusal controls, deterministic regeneration, definition-level identity, and ledgered outputs. VALO adopts only the general verification pattern and preserves its independent execution-governance architecture and terminology.
