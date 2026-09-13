# Work anchor — purpose-bound execution risk

- Repo: `nsolland/valo-reht`
- Canonical base SHA: `f43a1917c665fab5c0ca9d4339e4a3edb78733ca`
- Branch: `feat/purpose-bound-execution-risk`
- Draft PR: `#6`
- Claim / owner: ChatGPT for Njål Gaute Solland
- Owned files:
  - `docs/work-anchors/2026-08-11-purpose-bound-execution-risk.md`
  - `src/valo_reht/execution_requirements.py`
  - `src/valo_reht/reht.py`
  - `tests/test_execution_requirements.py`
  - `docs/EXECUTION_AUTHORIZATION_REQUIREMENTS_V1.md`
- Dependencies: frozen Kernel v1 Purpose and Authority contracts; no Kernel/ISA/Function Fabric edits
- Scope: close the execution-governance gap where a valid or compromised identity/authority can reach a consequential action without a verified purpose binding. Harden EAR v1 so high-impact, irreversible, or explicitly purpose-required actions fail closed unless purpose is explicit, current, scoped to the target/action, and explicitly bound by authority.
