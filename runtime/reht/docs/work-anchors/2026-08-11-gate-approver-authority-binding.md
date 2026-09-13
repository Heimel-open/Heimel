# Work anchor — gate approver authority binding

- Repo: `nsolland/valo-reht`
- Canonical base SHA: `97bb143d9a56c122296681d930db7697e7583d29`
- Branch: `feat/gate-approver-authority-binding`
- PR: `#11`
- Claim / owner: ChatGPT for Njål Gaute Solland
- Owned files:
  - `docs/work-anchors/2026-08-11-gate-approver-authority-binding.md`
  - `src/valo_reht/approver_authority.py`
  - `src/valo_reht/execution_requirements.py`
  - `tests/test_execution_requirements.py`
  - `tests/test_aas_gate_contract.py`
  - `.github/workflows/ci.yml`
- Dependencies: nonce-bound `EAR_GATE_V1`; AAS approver-authority producer merged at `1b52dcbac4646ec37694329372881008a6bec43b`; existing Workflow ISA / Kernel CI pins
- Scope: require human-approval and dual-control gate attestations to prove each approver has current approval authority for the exact action target, purpose and action hash. Approval authority evidence is a gate condition only and cannot create execution authority.
