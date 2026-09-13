# Work anchor — effect-boundary conformance

- Active delivery: define Kernel-side `NO_DIRECT_EFFECT_PATH`, `NULL_EFFECT_ON_DENY`, structural-coupling and deterministic boundary-replay contracts without changing component ownership.
- Repository: `nsolland/valo-kernel`
- Canonical base: `84c6f5e2d0ca0e7cd4c1fbaef9b3e004165d39fe` (includes merged TEE governed-workspace work).
- Initial claim base: `3d87c67fc57682a03539361bef033a1e22e6764c`.
- Branch: `feat/effect-boundary-conformance`
- Owner/claim: Codex `/root` on behalf of Njål.
- Owned files:
  - `AGENTS.md`
  - `docs/effect_boundary_conformance_v1.md`
  - `tests/test_effect_boundary_contract.py`
  - this work anchor
- Verification: 184 tests pass; Python compileall and Ruff pass after reconciliation with current main.
- Dependencies: Kernel remains governed state/contracts; REHT remains fresh exact-action authorization; RACS remains the deterministic decision contract; Gateway remains bounded enforcement; Veritas remains evidence/outcome verification.
- External dependencies: none. GATE, Microsoft AGT and z-gateway are evidence only.
