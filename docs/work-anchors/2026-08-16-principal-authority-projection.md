# Work anchor — principal-side authority projection

- Repo: `nsolland/valo-kernel`
- Canonical base SHA: `84c6f5e2d0ca0e7cd4c1fbaef9b3e004165d39fe`
- Branch: `feat/principal-authority-projection`
- Draft PR: `#33`
- Claim / owner: ChatGPT for Njål Gaute Solland
- Owned files:
  - `docs/work-anchors/2026-08-16-principal-authority-projection.md`
  - `src/valo_kernel/authority_projection.py`
  - `tests/test_authority_projection.py`
  - `docs/principal_authority_projection.md`
  - `src/valo_kernel/__init__.py`
- Dependencies: existing frozen Kernel Authority/Delegation/Purpose contracts; existing ProposedAction contract; no REHT/RACS/Gateway semantic changes
- Active delivery: prove that one canonical principal-side Authority/Delegation/Purpose model can project the same bounded execution decision into multiple bank/rail adapters without changing authority semantics.
- Invariants: `NO_AUTHORITY_CREATION`; adapters may narrow or reject but never widen principal authority; no sensitive full authority-state export to workers or rails; fresh state binding is explicit and fail-closed.
