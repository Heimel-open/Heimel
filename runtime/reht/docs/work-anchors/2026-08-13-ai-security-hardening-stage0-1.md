# Work anchor — AI security hardening stages 0-1

- Repo: `nsolland/valo-reht`
- Canonical base SHA: `53d505fab634627fe825dcdb57110acf6724c158`
- Branch: `feat/ai-security-hardening-stage0-1`
- Owner: nsolland
- Delivery: Stage 0 executable assurance manifest + Stage 1 cross-stack non-bypass conformance
- Owned files:
  - `security/ai_security_closure_2026.json`
  - `src/valo_reht/security_assurance.py`
  - `tests/test_assurance_manifest.py`
  - `tests/test_security_non_bypass_stage1.py`
  - `.github/workflows/ci.yml`
- Pinned dependency anchors: `valo-gateway@c149b3f5046294e5777aa36389c4d0b6f3cf83c4`, `valo-platform@4e25334058f15c4715cf818954957103eaba716b`, `Racs@1fb87c79a68afc9c9b47b3fa5f5a00b65c1fa7e1`, `Veritas@00d9c6777402f5dff093ea6b108b1583b87b6364`.
- Evidence: CI run `31743549292` passed dependency fetch/install, compileall, Ruff and pytest.
- Invariants preserved: REHT remains sole authorization boundary; RACS remains deterministic contract-only; Gateway remains mechanical; external adapters remain optional and non-authoritative.
- Status: READY TO MERGE.
