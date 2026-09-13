# Sentry coding-agent adapter claim

- Repo: `nsolland/valo-factory`
- Canonical base SHA: `d23499d3a8d6936ab6e0d1ddf8297e3453d989fd`
- Branch: `feat/sentry-coding-agent-adapter`
- Owner: `nsolland`
- Active delivery: Sentry incident adapter that normalizes production evidence, launches replaceable coding-agent repair work, and verifies post-deploy outcome without granting execution authority
- Owned files:
  - `connectors/sentry/*`
  - `tests/test_sentry_adapter.py`
  - `docs/architecture/sentry-coding-agent-adapter.md`
  - `work/SENTRY_CODING_AGENT_ADAPTER_CLAIM.md`
- Dependencies:
  - Sentry issue/event/trace evidence
  - replaceable coding-agent provider such as Cursor
  - Factory validation/evaluation pipeline
  - REHT authorization before consequential merge/deploy actions
  - Veritas receipts after execution
- Scope rule: Sentry and coding-agent providers are evidence and repair adapters only; they may not authorize merge, deploy, data mutation, or other consequential execution.
