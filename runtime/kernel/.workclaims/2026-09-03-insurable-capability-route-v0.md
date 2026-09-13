# Work claim — Insurable Capability Route v0

- Owner: `nsolland`
- Canonical base: `0a8205f8a3c169eede7b7d8e50c4d66a950d5c32`
- Branch: `feature/insurable-capability-route-v0`
- Primary objective: make one capability route mechanically assessable for execution admissibility and residual underwriting risk, ending in verifiable evidence.
- Owned files:
  - `src/valo_kernel/kernel/insurable_route.py`
  - `examples/demonstrator_8_insurable_capability_route_v0.py`
  - `tests/test_insurable_capability_route_v0.py`
  - `docs/insurable_capability_route_v0.md`
  - this claim
- Dependencies: existing compute-route assessment, fresh downstream REHT authorization boundary, canonical digests, effect/evidence receipt semantics.
- Non-goal: insurer pricing, actuarial calibration, insurer-specific policy language, payment-provider integration.
