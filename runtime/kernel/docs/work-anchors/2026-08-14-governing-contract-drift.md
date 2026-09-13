# Work anchor — governing contract drift

- Active delivery: close governing-contract drift during a governed continuation.
- Repository: `nsolland/valo-kernel`
- Canonical base: `1626daf49b0eacc422efb6f20140ad2b6dfed42b`
- Branch: `fix/governing-contract-drift`
- Owner/claim: ChatGPT on behalf of Njål; governed workspace contract freshness.
- Owned files:
  - `src/valo_kernel/contracts/workspace.py`
  - `src/valo_kernel/kernel/workspace.py`
  - `tests/test_governing_contract_drift.py`
  - `docs/governing_contract_drift_v1.md`
  - `docs/governed_workspace_v1.md`
  - `AGENTS.md`
  - this work anchor
- Dependencies: existing Kernel Contract state, dependency digests, workspace sealing and fresh downstream REHT authorization.
- External dependencies: none.
