# Work anchor: Bazoom content adapter

- Primary objective: automate Bazoom content-production and review workflows on top of Function Fabric without creating a separate execution stack.
- Canonical base SHA: `350a77527eadcab7ff33216a9db8c8549ce93a91`
- Branch: `feat/bazoom-content-adapter`
- Owner/claim: ChatGPT / active user-directed build
- Owned files:
  - `src/valo_function_fabric/adapters/bazoom.py`
  - `src/valo_function_fabric/adapters/__init__.py`
  - `tests/test_bazoom_adapter.py`
  - `docs/work-anchors/2026-09-03-bazoom-content-adapter.md`
- Dependencies: existing Function Fabric contracts only; no Bazoom API dependency in MVP.
- Active delivery: deterministic brief/article validation, human-review gate, and explicit block for `NO use of AI` production tasks.
- Non-goals: browser automation, credential handling, automatic submission, or bypassing client restrictions.
