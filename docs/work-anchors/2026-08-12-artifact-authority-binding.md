# Work anchor — artifact authority binding

- Active delivery: make the no-authority-by-artifact rule executable in the
  governed workspace candidate contract.
- Repository: `nsolland/valo-kernel`
- Canonical base: `f0052ae13b1a91246f18f5e08620b543cdb90923`
- Branch: `feat/artifact-authority-binding`
- Owner/claim: ChatGPT on behalf of Njål; artifact continuation contract.
- Owned files:
  - `src/valo_kernel/__init__.py`
  - `src/valo_kernel/contracts/__init__.py`
  - `src/valo_kernel/contracts/workspace.py`
  - `tests/test_admission.py`
  - `tests/test_artifact_authority_binding.py`
  - `docs/artifact_authority_binding_v1.md`
  - `docs/governed_workspace_v1.md`
  - `docs/work-anchors/2026-08-12-artifact-authority-binding.md`
- Dependencies: existing governed workspace digest, candidate sealing,
  deterministic conformance and fresh downstream REHT authorization.
- External dependencies: none.
