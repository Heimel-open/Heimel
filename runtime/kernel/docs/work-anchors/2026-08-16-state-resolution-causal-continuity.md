# Work anchor — state resolution and causal continuity

- Repo: `nsolland/valo-kernel`
- Canonical base SHA: `69831c232a00ab418a9b881f13d0eb605d3983fb`
- Branch: `feat/state-resolution-causal-continuity`
- Draft PR: `#34`
- Claim / owner: ChatGPT for Njål Gaute Solland
- Owned files:
  - `docs/work-anchors/2026-08-16-state-resolution-causal-continuity.md`
  - `src/valo_kernel/state_resolution.py`
  - `tests/test_state_resolution.py`
  - `tests/test_state_resolution_digest_binding.py`
  - `docs/state_resolution_causal_continuity.md`
  - `docs/principal_authority_projection.md`
  - `src/valo_kernel/__init__.py`
- Dependencies: existing Kernel Authority/Delegation/Purpose contracts; existing principal authority projection from PR #33; canonical digest utilities; no REHT/RACS/Gateway semantic ownership changes.
- Active delivery: make commit-time authority state resolution source-bound, provenance/version aware and causally continuous; temporal freshness alone must never establish commit eligibility.
- Invariants: source systems remain authoritative for their facts; resolver creates no authority and no synthetic truth; required facts must be present and source-valid; bounded staleness must be explicit; causal continuity is mandatory for authority-critical dependencies; uncertainty or continuity failure fails closed before REHT commitment; opaque dependency binding must include accepted continuity evidence.
