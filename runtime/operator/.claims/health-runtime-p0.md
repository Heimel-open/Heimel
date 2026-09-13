# Health Pack runtime P0.1 claim

- issue: #12
- owner: Codex / health-runtime worker
- base: `23b1c37f70b977fe2990c33cea35b170c737a448`
- branch: `feat/health-runtime-p0`
- owned paths: `src/valo_health_pack/world.py`, `src/valo_health_pack/ports.py`, health runtime exports, `src/valo_operator/surfaces.py`, `src/valo_operator/__init__.py`, focused tests
- dependencies: pinned Kernel / Function Fabric / Workflow ISA / valo-reht used by Operator CI
- boundary: HealthKernel validates domain state only; REHT remains sole execution authorization boundary
