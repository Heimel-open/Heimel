# Work anchor — gate execution-nonce binding

- Repo: `nsolland/valo-reht`
- Canonical base SHA: `1d142e932c1e3a5f632849809f426992c2f1c428`
- Branch: `feat/gate-execution-nonce-binding`
- Draft PR: `#10`
- Claim / owner: ChatGPT for Njål Gaute Solland
- Owned files:
  - `docs/work-anchors/2026-08-11-gate-execution-nonce-binding.md`
  - `src/valo_reht/execution_requirements.py`
  - `tests/test_execution_requirements.py`
  - `tests/test_aas_gate_contract.py`
  - `.github/workflows/ci.yml`
  - `docs/EXECUTION_AUTHORIZATION_REQUIREMENTS_V1.md`
- Dependencies: `action-attestation-service` pinned to nonce-bound producer `c5f45d0837dcabaff52f6c67a38479160164bda0`; existing Workflow ISA / Kernel CI pins
- Scope: require every protected EAR_GATE_V1 attestation to carry the exact current execution_nonce. An approval for one execution attempt must fail closed on another attempt even when actor and action contract are otherwise identical. No new layer; REHT remains sole authorization boundary.
