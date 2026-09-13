# Work anchor — production effect boundary

Repository: `nsolland/valo-reht`
Canonical base SHA: `75f8b9d57f82355204b9a965123a842b345ac2f2`
Branch: `fix/production-effect-boundary`
Owner: Njål / active fix
Owned files:
- `src/valo_reht/effect_boundary.py`
- `src/valo_reht/__init__.py`
- `tests/test_effect_boundary.py`
- `tests/test_production_effect_boundary_integration.py`
- `docs/evidence/production_effect_boundary_fix_2026-08-23.md`
- `docs/work-anchors/2026-08-23-production-effect-boundary.md`
Dependency: merged two-core runtime from PR #37.

Primary objective: replace the TEST-ONLY effect-boundary caveat with a production mechanical effect boundary inside `valo-reht`, without creating a third authority core.
