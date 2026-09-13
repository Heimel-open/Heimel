# Work anchor — AAS to REHT gate contract

- Repo: `nsolland/valo-reht`
- Canonical base SHA: `9d49a12ad0d2ad58f886e21fdaad66268272365c`
- Branch: `test/aas-reht-gate-contract`
- Draft PR: `#8`
- Claim / owner: ChatGPT for Njål Gaute Solland
- Owned files:
  - `docs/work-anchors/2026-08-11-aas-reht-gate-contract.md`
  - `.github/workflows/ci.yml`
  - `tests/test_aas_gate_contract.py`
- Dependencies: `action-attestation-service` pinned at `9fb58c6de287459ae2dd28525ef8b340284267a7`; existing frozen Workflow ISA / Kernel CI dependencies
- Scope: prove the real producer-consumer contract from trusted signed AAS gate records through `build_reht_gate_context()` into REHT EAR v1. Valid high-impact execution may pass only when all other authority/purpose requirements also hold; missing, spoofed or stale-for-modified-action gate evidence fails closed.
