# Work claim: Execution Authority Assurance

Owner: ChatGPT on behalf of Njål / VALO
Canonical base: 5e940de435856d24827b7eb05f31a9400a8dbb81
Branch: feat/execution-authority-assurance

Active delivery: close the production gaps between principal authority and regulated settlement by adding signed bounded execution leases, revocation-epoch convergence, bank acceptance and settlement evidence contracts.

Owned files:
- src/valo_kernel/execution_authority_assurance.py
- tests/test_execution_authority_assurance.py
- docs/execution_authority_assurance_v1.md
- src/valo_kernel/__init__.py
- .workclaims/execution-authority-assurance.md

Dependencies:
- existing Authority / Delegation / Purpose contracts
- existing AuthorityStateReference and canonical digest semantics
- existing REHT/RACS/Gateway/Veritas boundaries remain external and authoritative
- Ed25519 reference signing may be replaced by HSM/KMS adapters in production

Invariants:
- a lease can only attenuate existing authority; it never creates authority
- every consequence-bearing action still requires a fresh REHT/RACS decision
- push revocation is never trusted alone: short validity + epoch equality + local acknowledgement are required
- stale, unknown, partitioned, replayed or widened authority fails closed
- bank acceptance is a separate regulated-node decision and cannot rewrite enterprise authority
- settlement evidence must bind the exact accepted action/execution/effect
- cryptographic signatures prove integrity/authenticity of artifacts, not legal validity or truth of external state
- no direct effect path is introduced
