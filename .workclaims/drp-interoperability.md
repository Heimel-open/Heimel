# Work claim: DRP interoperability

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: 0b50c18bbcc59bf36e26a8613e33142b34f30764
Branch: feat/drp-interoperability

Active delivery: add a provider-neutral interoperability boundary for draft-nelson-agent-delegation-receipts-10 without importing DRP authorization semantics into Kernel or weakening fresh commit-time REHT evaluation.

Owned files:
- src/valo_kernel/contracts/drp.py
- src/valo_kernel/kernel/drp_adapter.py
- tests/test_drp_interoperability.py
- docs/drp_interoperability_v1.md
- .workclaims/drp-interoperability.md

Dependencies:
- existing Authority and Delegation contracts
- existing deterministic canonical_digest helper
- external signature/log verification remains upstream evidence, not Kernel authority
- REHT/RACS/Gateway/Veritas remain external execution-governance boundaries

Invariants:
- DRP receipt evidence creates no authority and issues no clearance
- delegation may narrow but never widen authority
- parent denials and tighter validity constraints must survive descendant delegation
- revocation of an ancestor invalidates affected descendant authority at execution time
- authority-state drift is fail-closed for VALO even when an imported DRP reauth policy would permit with a soft signal
- receipt validity is necessary evidence, never sufficient authorization for consequence-bearing execution
- no direct effect path is introduced
