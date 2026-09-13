# Work anchor — AAS key lifecycle to REHT contract

- Repo: `nsolland/valo-reht`
- Canonical base SHA: `790b28c537a6e1bd3e7c1de1c71f4177f045a2aa`
- Branch: `test/aas-key-lifecycle-contract`
- Draft PR: `#9`
- Claim / owner: ChatGPT for Njål Gaute Solland
- Owned files:
  - `docs/work-anchors/2026-08-11-aas-key-lifecycle-contract.md`
  - `.github/workflows/ci.yml`
  - `tests/test_aas_gate_contract.py`
- Dependencies: `action-attestation-service` pinned at `e73f5c364a614a1bc51e4a56edc0183614e3b875`; existing Workflow ISA / Kernel CI pins
- Scope: update the producer-consumer contract gate to current AAS key-lifecycle semantics. Prove trusted active key can supply a valid high-impact gate to REHT while unknown, wrong-key, expired or revoked signing keys cannot produce a REHT gate context.
