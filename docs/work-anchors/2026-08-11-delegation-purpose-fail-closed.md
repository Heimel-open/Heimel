# Work anchor — delegation purpose fail-closed invariant

- Repo: `nsolland/valo-kernel`
- Canonical base SHA: `4a6becd8a7a4af711f55001a9b6ed273794f929a`
- Branch: `test/delegation-purpose-fail-closed`
- Draft PR: `#6`
- Claim / owner: ChatGPT for Njål Gaute Solland
- Owned files:
  - `docs/work-anchors/2026-08-11-delegation-purpose-fail-closed.md`
  - `tests/test_execution_context.py`
- Dependencies: existing frozen Kernel Authority/Delegation/Purpose contracts; no REHT/ISA/Function Fabric edits
- Scope: prove the current fail-closed behavior that an active Delegation is context only and cannot become executable Authority by itself. Preserve `purpose_restriction` as explicit delegation data so any future delegated-authority derivation must deliberately narrow and carry it rather than silently dropping it.
