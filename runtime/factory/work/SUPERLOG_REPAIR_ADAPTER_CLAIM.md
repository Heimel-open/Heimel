# Superlog repair adapter claim

- Repo: `nsolland/valo-factory`
- Canonical base SHA: `2145de002900d61940567f0ea66d28c1a9b2047d`
- Branch: `feat/superlog-repair-adapter`
- Owner: `nsolland`
- Active delivery: external repair-agent adapter for alert-driven investigation and patch proposal, with no execution authority
- Owned files:
  - `connectors/superlog/*`
  - `tests/test_superlog_adapter.py`
  - `docs/architecture/superlog-repair-adapter.md`
  - `work/SUPERLOG_REPAIR_ADAPTER_CLAIM.md`
- Dependencies:
  - observability inputs such as Sentry/Datadog-compatible alerts and traces
  - repository/context read access
  - Factory validation/evaluation pipeline
  - REHT authorization before consequential merge/deploy actions
  - Veritas receipts after execution
- Scope rule: the adapter may investigate and propose patches; it may not authorize merge, deploy, data mutation, or other consequential execution.
